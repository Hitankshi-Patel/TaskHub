"""
worker.py
=========
Background job runner for TaskHub image generation.

Image type → pipeline strategy:
  white_background  → build_white_background()      (pure Pillow, zero API)
  theme_1           → Unsplash "white marble..."     + build_static_composite()
  theme_2           → Unsplash "dark navy velvet..." + build_static_composite()
  creative_1        → Unsplash "golden hour beach..."+ build_static_composite(blur_bg=True)
  creative_2        → Unsplash "rose garden bokeh..."+ build_static_composite(blur_bg=True)
  model_front / model_side / model_close
                    → Google Gemini 3.1 Flash Image (ModelImageGenerator)
                      All three model images are generated in one job call;
                      individual model_ jobs are no-ops if already generated.

Foundation for all 8: rembg local ONNX background removal, result cached to disk
and path stored on Task.rembg_cache_path.
"""

import time
import uuid
import os
import sys
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import current_app

# Ensure the backend directory is on the path for standalone / Vercel execution
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, GeneratedImage, Task, AuditLog

# ---------------------------------------------------------------------------
# Global job registry
# Structure: { job_id: { status, result, error, progress, created_at } }
# ---------------------------------------------------------------------------
JOBS: dict = {}

executor = ThreadPoolExecutor(max_workers=5)
app_ref = None  # Set by init_worker()


def init_worker(app):
    global app_ref
    app_ref = app


def get_job_status(job_id: str):
    return JOBS.get(job_id)


def run_in_context(func, *args, **kwargs):
    if not app_ref:
        raise ValueError("Worker has not been initialised with a Flask app reference.")
    with app_ref.app_context():
        return func(*args, **kwargs)


def start_background_job(job_func, *args, **kwargs) -> str:
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "pending",
        "result": None,
        "error": None,
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
    }

    def task_wrapper():
        try:
            JOBS[job_id]["status"] = "running"
            JOBS[job_id]["progress"] = 10
            result = run_in_context(job_func, job_id, *args, **kwargs)
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["result"] = result
            JOBS[job_id]["progress"] = 100
        except Exception as exc:
            import traceback
            traceback.print_exc()
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(exc)
            JOBS[job_id]["progress"] = 100

    executor.submit(task_wrapper)
    return job_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _download_product_image(url: str) -> bytes:
    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        raise ValueError(f"Failed to fetch product image from {url} (HTTP {resp.status_code})")
    return resp.content


def _detect_category(task_title: str) -> str:
    title = (task_title or "").lower()
    if any(w in title for w in ("necklace", "pendant", "chain")):
        return "necklace"
    if any(w in title for w in ("ring", "band")):
        return "ring"
    if any(w in title for w in ("earring", "stud")):
        return "earring"
    if any(w in title for w in ("bracelet", "bangle", "watch")):
        return "bracelet"
    return "general"


# ---------------------------------------------------------------------------
# Main generation job
# ---------------------------------------------------------------------------

def generate_task_image_job(job_id: str, task_id: str,
                             image_type: str, angle: str | None = None):
    """
    Background job that generates one of the 8 product images for *task_id*.

    Progress milestones (stored in JOBS[job_id]["progress"]):
      10  — job started
      25  — product image downloaded
      45  — rembg extraction complete (or cache hit)
      70  — image generation / compositing complete
      85  — upload complete
      100 — DB record written, done
    """
    from services.image_pipeline import (
        get_or_create_rembg_cache,
        build_white_background,
        fetch_unsplash_background,
        build_static_composite,
        UNSPLASH_QUERIES,
    )
    from services.ai_studio import upload_to_storage

    # ---- 1. Fetch task ----
    task = Task.query.get(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found.")

    # ---- 2. Download product image ----
    JOBS[job_id]["progress"] = 25
    print(f"[Job {job_id[:8]}] Downloading product image...")
    original_bytes = _download_product_image(task.product_image_url)
    print(f"[Job {job_id[:8]}] Product image downloaded ({len(original_bytes)} bytes).")

    # ---- 3. rembg background removal (cached per task) ----
    JOBS[job_id]["progress"] = 35
    print(f"[Job {job_id[:8]}] Extracting product with rembg...")
    transparent_bytes = get_or_create_rembg_cache(task, original_bytes)
    JOBS[job_id]["progress"] = 45
    print(f"[Job {job_id[:8]}] Transparent PNG ready ({len(transparent_bytes)} bytes).")

    # ---- 4. Generate / composite the image ----
    JOBS[job_id]["progress"] = 50
    composite_bytes: bytes
    prompt_used: str
    model_used: str

    if image_type == "white_background":
        # Pure Pillow — zero external calls
        print(f"[Job {job_id[:8]}] Building white background composite...")
        composite_bytes = build_white_background(transparent_bytes)
        prompt_used = "white #FFFFFF canvas — pure Pillow composite"
        model_used = "pillow"

    elif image_type in ("theme_1", "theme_2", "creative_1", "creative_2"):
        # Unsplash real photo + Pillow composite
        query = UNSPLASH_QUERIES[image_type]
        blur_bg = image_type in ("creative_1", "creative_2")
        print(f"[Job {job_id[:8]}] Fetching Unsplash background: '{query}'...")
        bg_bytes = fetch_unsplash_background(query)
        print(f"[Job {job_id[:8]}] Compositing product on background...")
        composite_bytes = build_static_composite(
            bg_bytes, transparent_bytes, blur_bg=blur_bg
        )
        prompt_used = f"Unsplash query: '{query}'"
        model_used = "unsplash+pillow"

    elif image_type in ("model_front", "model_side", "model_close"):
        # Google Gemini 3.1 Flash Image — generate all three model images in one call
        from services.model_image_generator import ModelImageGenerator

        jewelry_desc = getattr(task, "description", None) or ""
        print(
            f"[Job {job_id[:8]}] Generating all 3 model images via Gemini "
            f"(task: {task_id}, jewelry: {jewelry_desc[:60] or 'fallback'}...)..."
        )
        gen = ModelImageGenerator()
        model_images = gen.generate_all_three(
            task_id=task_id,
            jewelry_description=jewelry_desc,
            product_image_bytes=original_bytes,
        )

        # model_images = {"front": bytes, "side": bytes, "closeup": bytes}
        # Upload each angle and write a DB record for it.
        JOBS[job_id]["progress"] = 70
        angle_map = {
            "front":   "model_front",
            "side":    "model_side",
            "closeup": "model_close",
        }
        for angle_key, img_type_key in angle_map.items():
            img_bytes = model_images[angle_key]
            rand_suffix = str(uuid.uuid4())[:8]
            storage_path = f"{task_id}/composite_{img_type_key}_{rand_suffix}.png"
            print(f"[Job {job_id[:8]}] Uploading {img_type_key} to {storage_path}")
            generated_url = upload_to_storage(img_bytes, storage_path)

            sub_img_id = str(uuid.uuid4())
            gen_img_rec = GeneratedImage(
                id=sub_img_id,
                task_id=task_id,
                image_type=img_type_key,
                image_url=generated_url,
                prompt_used=(
                    f"Gemini 3.1 Flash Image — angle: {angle_key}, "
                    f"jewelry: {jewelry_desc[:120] or 'fallback'}"
                ),
                angle=angle_key,
                meta_data={
                    "job_id": job_id,
                    "generation_model": "gemini-3.1-flash-image",
                },
            )
            db.session.add(gen_img_rec)

            log = AuditLog(
                user_id=task.assigned_to,
                action="image_generated",
                table_name="generated_images",
                record_id=sub_img_id,
                new_values={
                    "task_id": task_id,
                    "image_type": img_type_key,
                    "image_url": generated_url,
                    "model": "gemini-3.1-flash-image",
                },
            )
            db.session.add(log)

        db.session.commit()
        JOBS[job_id]["progress"] = 100
        print(f"[Job {job_id[:8]}] All 3 model images generated and saved for task {task_id}.")
        # Return the record for the angle that was originally requested
        requested_angle = image_type.replace("model_", "")  # front / side / close
        if requested_angle == "close":
            requested_angle = "closeup"
        return {
            "task_id": task_id,
            "image_type": image_type,
            "message": "All 3 model images generated via Gemini 3.1 Flash Image.",
        }

    else:
        raise ValueError(f"Unknown image_type: '{image_type}'")

    JOBS[job_id]["progress"] = 70
    print(f"[Job {job_id[:8]}] Image generation complete.")

    # ---- 5. Upload to storage ----
    JOBS[job_id]["progress"] = 75
    rand_suffix = str(uuid.uuid4())[:8]
    storage_path = f"{task_id}/composite_{image_type}_{rand_suffix}.jpg"
    print(f"[Job {job_id[:8]}] Uploading to storage: {storage_path}")
    generated_url = upload_to_storage(composite_bytes, storage_path)
    JOBS[job_id]["progress"] = 85
    print(f"[Job {job_id[:8]}] Uploaded: {generated_url}")

    # ---- 6. Persist to DB ----
    # Pre-generate the ID so it's available for the AuditLog before the flush.
    new_img_id = str(uuid.uuid4())
    gen_img = GeneratedImage(
        id=new_img_id,
        task_id=task_id,
        image_type=image_type,
        image_url=generated_url,
        prompt_used=prompt_used,
        angle=angle,
        meta_data={
            "job_id": job_id,
            "generation_model": model_used,
            "category_detected": _detect_category(task.title),
        },
    )
    db.session.add(gen_img)

    log = AuditLog(
        user_id=task.assigned_to,
        action="image_generated",
        table_name="generated_images",
        record_id=new_img_id,
        new_values={
            "task_id": task_id,
            "image_type": image_type,
            "image_url": generated_url,
            "model": model_used,
        },
    )
    db.session.add(log)
    db.session.commit()
    JOBS[job_id]["progress"] = 100

    print(f"[Job {job_id[:8]}] Done — {image_type} saved as {gen_img.id}.")
    return gen_img.to_dict()
