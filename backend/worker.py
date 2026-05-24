import time
import uuid
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import current_app

# Ensure the backend directory is in the path for standalone Vercel deployments and local execution
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, GeneratedImage, Task, AuditLog

# Global job dictionary
# Structure: { job_id: { "status": "pending"|"running"|"completed"|"failed", "result": data, "error": msg, "progress": int } }
JOBS = {}

# Initialize thread pool executor
executor = ThreadPoolExecutor(max_workers=5)

# Hold reference to Flask app for context
app_ref = None

def init_worker(app):
    global app_ref
    app_ref = app

def get_job_status(job_id):
    """
    Retrieves the status of a background job.
    """
    return JOBS.get(job_id)

def run_in_context(func, *args, **kwargs):
    """
    Helper to run a function inside the Flask app context.
    """
    if not app_ref:
        raise ValueError("Worker is not initialized with a Flask app reference.")
    with app_ref.app_context():
        return func(*args, **kwargs)

def start_background_job(job_func, *args, **kwargs):
    """
    Submits a job to the thread pool and returns the job ID.
    """
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "pending",
        "result": None,
        "error": None,
        "progress": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Define the actual task wrapper
    def task_wrapper():
        try:
            JOBS[job_id]["status"] = "running"
            JOBS[job_id]["progress"] = 10
            
            # Execute with Flask App context
            result = run_in_context(job_func, job_id, *args, **kwargs)
            
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["result"] = result
            JOBS[job_id]["progress"] = 100
        except Exception as e:
            import traceback
            traceback.print_exc()
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
            JOBS[job_id]["progress"] = 100

    executor.submit(task_wrapper)
    return job_id

# The AI Generation background task
def generate_task_image_job(job_id, task_id, image_type, angle=None):
    """
    Background job that:
    1. Downloads original product image.
    2. Runs background removal (via Replicate API or locally).
    3. Generates environment background via Google Gemini Imagen.
    4. Resizes and overlays the product on the generated background using PIL.
    5. Saves composite image to database and storage.
    """
    from services.ai_studio import (
        extract_product_background,
        upload_to_storage,
        get_generation_prompts,
        generate_background_scene,
        prepare_product_overlay,
        composite_product_on_background
    )
    import requests
    
    # 1. Fetch Task
    task = Task.query.get(task_id)
    if not task:
        raise ValueError(f"Task with ID {task_id} not found.")
    
    JOBS[job_id]["progress"] = 20
    
    # 2. Download product image
    response = requests.get(task.product_image_url, timeout=15)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch original product image from {task.product_image_url}")
    
    original_bytes = response.content
    
    # 3. Extract background
    JOBS[job_id]["progress"] = 35
    print(f"[Job {job_id[:8]}] Step 3/7: Running background removal...")
    transparent_bytes = extract_product_background(original_bytes)
    print(f"[Job {job_id[:8]}] Step 3/7: Background removal complete.")
    
    # 4. Generate environment background using Gemini Imagen
    JOBS[job_id]["progress"] = 55
    prompts = get_generation_prompts(task.title, task.description, image_type, angle)
    print(f"[Job {job_id[:8]}] Step 4/7: Generating background with Imagen...")
    background_bytes = generate_background_scene(prompts["prompt"])
    print(f"[Job {job_id[:8]}] Step 4/7: Background scene ready.")
    
    # 5. Composite product on background
    JOBS[job_id]["progress"] = 75
    print(f"[Job {job_id[:8]}] Step 5/7: Compositing product on environment...")
    
    # Determine model/environment scaling & offset configurations based on product type
    title_lower = (task.title or "").lower()
    category = "general"
    if "ring" in title_lower or "band" in title_lower:
        category = "ring"
    elif "earring" in title_lower or "stud" in title_lower:
        category = "earring"
    elif "necklace" in title_lower or "pendant" in title_lower or "chain" in title_lower:
        category = "necklace"
    elif "bracelet" in title_lower or "bangle" in title_lower or "watch" in title_lower:
        category = "bracelet"
        
    scale_factor = 0.55
    offset = (0, 0)
    add_reflection = False
    add_shadow = True
    
    if image_type == "theme_1":
        add_reflection = True
        
    if image_type.startswith("model_"):
        if category == "necklace":
            scale_factor = 0.35
            offset = (0, 100)
        elif category == "ring":
            scale_factor = 0.22
            offset = (0, 0)
        elif category == "earring":
            scale_factor = 0.20
            offset = (50, 50)
        else:
            scale_factor = 0.30
            offset = (0, 0)
            
    product_canvas = prepare_product_overlay(
        transparent_png_bytes=transparent_bytes,
        target_size=(1024, 1024),
        scale_factor=scale_factor,
        position_offset=offset
    )
    
    composite_bytes = composite_product_on_background(
        background_bytes=background_bytes,
        product_canvas_img=product_canvas,
        add_shadow=add_shadow,
        add_reflection=add_reflection
    )
    
    # 6. Upload final composite image
    JOBS[job_id]["progress"] = 85
    print(f"[Job {job_id[:8]}] Step 6/7: Uploading composite to Storage...")
    rand_suffix = str(uuid.uuid4())[:8]
    generated_url = upload_to_storage(composite_bytes, f"{task_id}/composite_{image_type}_{rand_suffix}.jpg")
    print(f"[Job {job_id[:8]}] Step 6/7: Composite uploaded.")
    
    # 7. Save to DB
    JOBS[job_id]["progress"] = 90
    gen_img = GeneratedImage(
        task_id=task_id,
        image_type=image_type,
        image_url=generated_url,
        prompt_used=prompts["prompt"],
        angle=angle,
        meta_data={
            "job_id": job_id,
            "generation_model": "imagen-3.0-generate-002",
            "category_detected": category,
            "scale_factor": scale_factor,
            "offset": offset
        }
    )
    db.session.add(gen_img)
    
    # Write Audit Log
    log = AuditLog(
        user_id=task.assigned_to,
        action="image_generated",
        table_name="generated_images",
        record_id=gen_img.id,
        new_values={
            "task_id": task_id,
            "image_type": image_type,
            "image_url": generated_url
        }
    )
    db.session.add(log)
    db.session.commit()
    
    return gen_img.to_dict()
