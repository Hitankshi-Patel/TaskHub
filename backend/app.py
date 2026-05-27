import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import firebase_admin
from firebase_admin import credentials, auth

from config import Config
from models import db, User, Task, GeneratedImage, AuditLog
from worker import init_worker, start_background_job, generate_task_image_job, get_job_status
from services.notifier import (
    notify_task_assigned,
    notify_task_submitted,
    notify_task_accepted,
    notify_revision_requested
)

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, resources={r"/api/*": {"origins": "*"}, r"/static/*": {"origins": "*"}})

firebase_initialized = False
try:
    if Config.FIREBASE_SERVICE_ACCOUNT_JSON:
        import json
        cred_dict = json.loads(Config.FIREBASE_SERVICE_ACCOUNT_JSON)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
    elif Config.FIREBASE_CREDENTIALS_PATH and os.path.exists(Config.FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
    else:
        firebase_admin.initialize_app()
        firebase_initialized = True
    print("Firebase Admin initialized successfully.")
except ValueError:
    firebase_initialized = True
except Exception as e:
    print(f"Warning: Firebase Admin failed to initialize: {e}. OAuth will require Debug Mocking.")

db.init_app(app)
init_worker(app)

def get_limiter_key():
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user.id
    return get_remote_address()

limiter = Limiter(
    key_func=get_limiter_key,
    app=app,
    default_limits=["100 per minute"],
    storage_uri="memory://"
)

print("Flask app initialized. DB tables will be verified on first request.")


def verify_firebase_token():
    if app.debug:
        mock_role = request.headers.get("X-Mock-Role")
        if mock_role:
            mock_id = f"mock-uid-{mock_role.lower()}"
            mock_email = f"{mock_role.lower()}@taskhub.dev"
            mock_name = f"Mock {mock_role.capitalize()}"
            return {"uid": mock_id, "email": mock_email, "name": mock_name, "role": mock_role.lower()}

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]

    if not firebase_initialized:
        return None

    try:
        return auth.verify_id_token(token)
    except Exception as e:
        err = str(e)
        if "too early" in err.lower():
            import time, re
            m = re.search(r'(\d+)\s*<\s*(\d+)', err)
            skew_secs = (int(m.group(2)) - int(m.group(1)) + 1) if m else 5
            if 0 < skew_secs <= 60:
                print(f"[auth] Clock skew detected ({skew_secs}s). Retrying...")
                time.sleep(skew_secs)
                try:
                    return auth.verify_id_token(token)
                except Exception as e2:
                    print(f"Firebase token verification failed (retry): {e2}")
                    return None
        print(f"Firebase token verification failed: {e}")
        return None


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token_data = verify_firebase_token()
        if not token_data:
            return jsonify({"error": "Unauthorized: Invalid or missing token"}), 401

        uid = token_data["uid"]
        email = token_data.get("email")
        name = token_data.get("name", "")

        user = User.query.get(uid)
        if not user:
            count = User.query.count()
            role = "admin" if count == 0 else token_data.get("role", "user")
            user = User(id=uid, email=email, full_name=name, role=role)
            db.session.add(user)
            db.session.commit()
            log = AuditLog(user_id=uid, action="user_registered", table_name="users", record_id=uid)
            db.session.add(log)
            db.session.commit()

        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token_data = verify_firebase_token()
        if not token_data:
            return jsonify({"error": "Unauthorized: Invalid or missing token"}), 401

        uid = token_data["uid"]
        user = User.query.get(uid)

        if not user and app.debug and token_data.get("role") == "admin":
            user = User(id=uid, email=token_data.get("email"), full_name=token_data.get("name"), role="admin")
            db.session.add(user)
            db.session.commit()

        if not user or user.role != "admin":
            return jsonify({"error": "Forbidden: Admin access required"}), 403

        g.current_user = user
        return f(*args, **kwargs)
    return decorated



@app.route("/api/auth/oauth/callback", methods=["POST"])
def oauth_callback():
    try:
        token_data = verify_firebase_token()
        if not token_data:
            data = request.get_json() or {}
            id_token = data.get("idToken")
            if id_token and firebase_initialized:
                try:
                    token_data = auth.verify_id_token(id_token)
                except Exception as e:
                    err = str(e)
                    if "too early" in err.lower():
                        import time, re
                        m = re.search(r'(\d+)\s*<\s*(\d+)', err)
                        skew_secs = (int(m.group(2)) - int(m.group(1)) + 1) if m else 5
                        if 0 < skew_secs <= 60:
                            print(f"[oauth_callback] Clock skew ({skew_secs}s). Retrying...")
                            time.sleep(skew_secs)
                            try:
                                token_data = auth.verify_id_token(id_token)
                            except Exception as e2:
                                return jsonify({"error": f"Invalid OAuth token: {str(e2)}"}), 401
                        else:
                            return jsonify({"error": f"Invalid OAuth token: {err}"}), 401
                    else:
                        return jsonify({"error": f"Invalid OAuth token: {err}"}), 401

        if not token_data:
            return jsonify({"error": "Unauthorized: Valid Firebase idToken required"}), 401

        uid = token_data["uid"]
        email = token_data.get("email")
        name = token_data.get("name", "")

        user = User.query.get(uid)
        if not user:
            count = User.query.count()
            role = "admin" if count == 0 else "user"
            user = User(id=uid, email=email, full_name=name, role=role)
            db.session.add(user)
            db.session.commit()
            log = AuditLog(user_id=uid, action="user_registered", table_name="users", record_id=uid)
            db.session.add(log)
            db.session.commit()

        return jsonify({"message": "Authentication successful", "user": user.to_dict()})
    except Exception as e:
        print(f"[oauth_callback] Unhandled error: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal server error during authentication"}), 500


@app.route("/api/auth/me", methods=["GET"])
@login_required
def auth_me():
    return jsonify({"user": g.current_user.to_dict()})


@app.route("/api/auth/users", methods=["GET"])
@admin_required
def list_users():
    users = User.query.filter_by(role='user').all()
    return jsonify([u.to_dict() for u in users])


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    return jsonify({"message": "Logged out successfully"})



@app.route("/api/tasks", methods=["POST"])
@admin_required
def create_task():
    data = request.get_json() or {}
    title = data.get("title")
    description = data.get("description")
    product_image_url = data.get("product_image_url")
    assigned_to = data.get("assigned_to")

    if not title or not product_image_url:
        return jsonify({"error": "Title and product_image_url are required"}), 400

    if assigned_to:
        assignee = User.query.get(assigned_to)
        if not assignee:
            return jsonify({"error": f"Assigned user with ID {assigned_to} not found"}), 404

    status = "assigned" if assigned_to else "pending"

    task = Task(
        title=title,
        description=description,
        product_image_url=product_image_url,
        status=status,
        assigned_to=assigned_to,
        created_by=g.current_user.id
    )
    db.session.add(task)
    db.session.commit()

    log = AuditLog(
        user_id=g.current_user.id,
        action="task_created",
        table_name="tasks",
        record_id=task.id,
        new_values=task.to_dict()
    )
    db.session.add(log)
    db.session.commit()

    if assigned_to:
        assignee = User.query.get(assigned_to)
        notify_task_assigned(
            user_email=assignee.email,
            user_name=assignee.full_name or assignee.email,
            task_title=task.title,
            task_id=task.id,
            task_description=task.description,
            product_image_url=task.product_image_url
        )

    return jsonify(task.to_dict()), 201


@app.route("/api/tasks", methods=["GET"])
@admin_required
def list_tasks():
    tasks = Task.query.all()
    task_list = []
    for task in tasks:
        td = task.to_dict()
        assignee = User.query.get(task.assigned_to) if task.assigned_to else None
        td["assignee_name"] = assignee.full_name or assignee.email if assignee else "Unassigned"
        task_list.append(td)
    return jsonify(task_list)


@app.route("/api/tasks/<id>/assign", methods=["POST"])
@admin_required
def assign_task(id):
    task = Task.query.get_or_404(id)
    data = request.get_json() or {}
    assigned_to = data.get("assigned_to")

    if not assigned_to:
        return jsonify({"error": "assigned_to is required"}), 400

    assignee = User.query.get(assigned_to)
    if not assignee:
        return jsonify({"error": "User not found"}), 404

    old_values = task.to_dict()
    task.assigned_to = assigned_to
    task.status = "assigned"

    log = AuditLog(
        user_id=g.current_user.id,
        action="task_assigned",
        table_name="tasks",
        record_id=task.id,
        old_values=old_values,
        new_values=task.to_dict()
    )
    db.session.add(log)
    db.session.commit()

    notify_task_assigned(
        user_email=assignee.email,
        user_name=assignee.full_name or assignee.email,
        task_title=task.title,
        task_id=task.id,
        task_description=task.description,
        product_image_url=task.product_image_url
    )

    return jsonify(task.to_dict())


@app.route("/api/tasks/<id>/accept", methods=["PUT"])
@admin_required
def accept_task(id):
    task = Task.query.get_or_404(id)
    data = request.get_json() or {}
    feedback = data.get("feedback", "Excellent photography work!")

    if task.status != "submitted":
        return jsonify({"error": "Only submitted tasks can be accepted"}), 400

    old_values = task.to_dict()
    task.status = "accepted"
    task.feedback = feedback

    for img in task.generations:
        img.is_final = True

    log = AuditLog(
        user_id=g.current_user.id,
        action="task_accepted",
        table_name="tasks",
        record_id=task.id,
        old_values=old_values,
        new_values=task.to_dict()
    )
    db.session.add(log)
    db.session.commit()

    assignee = User.query.get(task.assigned_to)
    if assignee:
        notify_task_accepted(
            user_email=assignee.email,
            user_name=assignee.full_name or assignee.email,
            task_title=task.title,
            feedback=feedback
        )

    return jsonify(task.to_dict())


@app.route("/api/tasks/<id>/request-revision", methods=["PUT"])
@admin_required
def request_revision(id):
    task = Task.query.get_or_404(id)
    data = request.get_json() or {}
    feedback = data.get("feedback")

    if not feedback:
        return jsonify({"error": "Feedback is required for revisions"}), 400

    if task.status != "submitted":
        return jsonify({"error": "Only submitted tasks can undergo revision"}), 400

    old_values = task.to_dict()
    task.status = "revision_requested"
    task.feedback = feedback

    log = AuditLog(
        user_id=g.current_user.id,
        action="task_revision_requested",
        table_name="tasks",
        record_id=task.id,
        old_values=old_values,
        new_values=task.to_dict()
    )
    db.session.add(log)
    db.session.commit()

    assignee = User.query.get(task.assigned_to)
    if assignee:
        notify_revision_requested(
            user_email=assignee.email,
            user_name=assignee.full_name or assignee.email,
            task_title=task.title,
            task_id=task.id,
            feedback=feedback
        )

    return jsonify(task.to_dict())


@app.route("/api/tasks/<id>", methods=["DELETE"])
@admin_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    log = AuditLog(
        user_id=g.current_user.id,
        action="task_deleted",
        table_name="tasks",
        record_id=id
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully"})



@app.route("/api/my-tasks", methods=["GET"])
@login_required
def get_my_tasks():
    tasks = Task.query.filter_by(assigned_to=g.current_user.id).all()
    return jsonify([t.to_dict() for t in tasks])


@app.route("/api/tasks/<id>", methods=["GET"])
@login_required
def get_task_details(id):
    task = Task.query.get_or_404(id)
    if g.current_user.role != "admin" and task.assigned_to != g.current_user.id:
        return jsonify({"error": "Forbidden: Not assigned to this task"}), 403
    return jsonify(task.to_dict())


@app.route("/api/tasks/<id>/start", methods=["PUT"])
@login_required
def start_task(id):
    task = Task.query.get_or_404(id)
    if task.assigned_to != g.current_user.id:
        return jsonify({"error": "Forbidden: Not assigned to this task"}), 403
    if task.status not in ["assigned", "revision_requested"]:
        return jsonify({"error": f"Cannot start task in state: {task.status}"}), 400

    old_values = task.to_dict()
    task.status = "in_progress"
    log = AuditLog(
        user_id=g.current_user.id,
        action="task_started",
        table_name="tasks",
        record_id=task.id,
        old_values=old_values,
        new_values=task.to_dict()
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(task.to_dict())


@app.route("/api/tasks/<id>/submit", methods=["POST"])
@login_required
def submit_task(id):
    task = Task.query.get_or_404(id)
    if task.assigned_to != g.current_user.id:
        return jsonify({"error": "Forbidden: Not assigned to this task"}), 403

    generations = GeneratedImage.query.filter_by(task_id=id).all()
    required_types = [
        "white_background", "theme_1", "theme_2",
        "creative_1", "creative_2",
        "model_front", "model_side", "model_close"
    ]
    generated_types = [gen.image_type for gen in generations]
    missing = [t for t in required_types if t not in generated_types]
    if missing:
        return jsonify({"error": "Cannot submit task. Missing generated images", "missing_types": missing}), 400

    old_values = task.to_dict()
    task.status = "submitted"
    log = AuditLog(
        user_id=g.current_user.id,
        action="task_submitted",
        table_name="tasks",
        record_id=task.id,
        old_values=old_values,
        new_values=task.to_dict()
    )
    db.session.add(log)
    db.session.commit()

    admin = User.query.filter_by(role="admin").first()
    if admin:
        notify_task_submitted(
            admin_email=admin.email,
            admin_name=admin.full_name or admin.email,
            task_title=task.title,
            task_id=task.id,
            user_name=g.current_user.full_name or g.current_user.email
        )

    return jsonify(task.to_dict())



@app.route("/api/tasks/<id>/generate", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def generate_image(id):
    task = Task.query.get_or_404(id)
    if task.assigned_to != g.current_user.id:
        return jsonify({"error": "Forbidden: Not assigned to this task"}), 403

    data = request.get_json() or {}
    image_type = data.get("image_type")
    angle = data.get("angle")

    valid_types = [
        "white_background", "theme_1", "theme_2",
        "creative_1", "creative_2", "model_front",
        "model_side", "model_close"
    ]
    if image_type not in valid_types:
        return jsonify({"error": f"Invalid image type. Must be one of: {valid_types}"}), 400

    job_id = start_background_job(
        generate_task_image_job,
        task_id=id,
        image_type=image_type,
        angle=angle
    )

    return jsonify({
        "job_id": job_id,
        "status": "pending",
        "message": "Image generation started."
    })


@app.route("/api/jobs/<job_id>/status", methods=["GET"])
@login_required
def job_status(job_id):
    status = get_job_status(job_id)
    if not status:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(status)


@app.route("/api/tasks/<id>/generations", methods=["GET"])
@login_required
def get_task_generations(id):
    task = Task.query.get_or_404(id)
    if g.current_user.role != "admin" and task.assigned_to != g.current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    generations = GeneratedImage.query.filter_by(task_id=id).order_by(GeneratedImage.created_at.desc()).all()
    return jsonify([gen.to_dict() for gen in generations])


@app.route("/api/generations/<id>", methods=["DELETE"])
@login_required
def delete_generation(id):
    gen = GeneratedImage.query.get_or_404(id)
    task = Task.query.get(gen.task_id)
    if task.assigned_to != g.current_user.id and g.current_user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    db.session.delete(gen)
    log = AuditLog(
        user_id=g.current_user.id,
        action="image_deleted",
        table_name="generated_images",
        record_id=id
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"message": "Generated image deleted successfully"})



@app.route("/api/admin/analytics", methods=["GET"])
@admin_required
def get_analytics():
    total_users = User.query.filter_by(role='user').count()
    total_tasks = Task.query.count()
    total_generations = GeneratedImage.query.count()

    status_counts = {
        "pending": Task.query.filter_by(status="pending").count(),
        "assigned": Task.query.filter_by(status="assigned").count(),
        "in_progress": Task.query.filter_by(status="in_progress").count(),
        "submitted": Task.query.filter_by(status="submitted").count(),
        "accepted": Task.query.filter_by(status="accepted").count(),
        "revision_requested": Task.query.filter_by(status="revision_requested").count(),
    }

    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(15).all()
    log_list = []
    for l in recent_logs:
        ld = l.to_dict()
        user = User.query.get(l.user_id) if l.user_id else None
        ld["user_email"] = user.email if user else "System"
        log_list.append(ld)

    return jsonify({
        "totals": {
            "users": total_users,
            "tasks": total_tasks,
            "generations": total_generations
        },
        "statuses": status_counts,
        "recent_activity": log_list
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    db_status = "disconnected"
    try:
        db.session.execute(db.text("SELECT 1"))
        db.session.commit()
        db.create_all()
        db_status = "connected"
    except Exception as e:
        print(f"[health_check] DB error: {e}")
        db.session.rollback()
        db_status = f"error: {str(e)}"

    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "firebase_auth": firebase_initialized,
        "database": db_status
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
