import time
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import current_app
from .models import db, GeneratedImage, Task, AuditLog

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
    2. Runs background removal.
    3. Uploads transparent product and mask to Storage.
    4. Constructs prompts.
    5. Calls Replicate SDXL inpainting.
    6. Saves new image URL to database.
    """
    from .services.ai_studio import (
        extract_product_background,
        prepare_inpainting_assets,
        upload_to_storage,
        get_generation_prompts,
        generate_inpaint_image
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
    
    # 3. Extract background (rembg downloads ~176MB u2net model on first run — this is normal)
    JOBS[job_id]["progress"] = 35
    print(f"[Job {job_id[:8]}] Step 3/7: Running background removal (rembg)... (first run downloads u2net model ~176MB)")
    transparent_bytes = extract_product_background(original_bytes)
    print(f"[Job {job_id[:8]}] Step 3/7: Background removal complete.")
    
    # 4. Prepare inpainting (base image + mask)
    JOBS[job_id]["progress"] = 50
    print(f"[Job {job_id[:8]}] Step 4/7: Preparing inpainting mask...")
    base_bytes, mask_bytes = prepare_inpainting_assets(transparent_bytes)
    print(f"[Job {job_id[:8]}] Step 4/7: Mask ready.")
    
    # 5. Upload assets to Storage
    rand_suffix = str(uuid.uuid4())[:8]
    print(f"[Job {job_id[:8]}] Step 5/7: Uploading base + mask to Supabase Storage...")
    base_url = upload_to_storage(base_bytes, f"{task_id}/base_{image_type}_{rand_suffix}.png")
    mask_url = upload_to_storage(mask_bytes, f"{task_id}/mask_{image_type}_{rand_suffix}.png")
    print(f"[Job {job_id[:8]}] Step 5/7: Assets uploaded.")
    JOBS[job_id]["progress"] = 70
    
    # 6. Generate prompts
    prompts = get_generation_prompts(task.description, image_type, angle)
    
    # 7. Run Replicate Inpainting
    JOBS[job_id]["progress"] = 80
    generated_url = generate_inpaint_image(
        base_url=base_url,
        mask_url=mask_url,
        prompt=prompts["prompt"],
        negative_prompt=prompts["negative_prompt"]
    )
    
    # 8. Save to DB
    JOBS[job_id]["progress"] = 90
    gen_img = GeneratedImage(
        task_id=task_id,
        image_type=image_type,
        image_url=generated_url,
        prompt_used=prompts["prompt"],
        angle=angle,
        meta_data={
            "job_id": job_id,
            "replicate_model": current_app.config.get("REPLICATE_INPAINT_MODEL"),
            "base_url": base_url,
            "mask_url": mask_url
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
