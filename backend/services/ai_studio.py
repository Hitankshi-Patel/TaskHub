"""
ai_studio.py
============
Storage helpers and legacy Pillow compositing utilities.

NOTE: The Replicate and Google Gemini Imagen approaches have been removed.
Background removal is now handled locally by rembg (see services/image_pipeline.py).
Backgrounds are either generated with pure Pillow (white canvas) or fetched from
the Unsplash API (photographic themes/creative). Model images are generated via
fal.ai FLUX/dev (also in services/image_pipeline.py).

Remaining functions kept here:
  - save_local_file()       — local filesystem fallback for image storage
  - upload_to_storage()     — Supabase Storage upload (with local fallback)
  - prepare_product_overlay()   — resize + centre-crop transparent PNG onto canvas
  - composite_product_on_background()  — final RGBA composite with shadow/reflection
"""

from __future__ import annotations

import io
import os
import requests
from PIL import Image
from config import Config


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def save_local_file(file_bytes: bytes, file_name: str) -> str:
    """
    Saves *file_bytes* to static/uploads/ and returns a localhost URL.
    Used as a fallback when Supabase Storage credentials are missing.

    *file_name* may contain subdirectory components (e.g. ``task_id/image.jpg``);
    the full directory tree is created automatically.
    """
    static_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static", "uploads"
    )
    # Normalise separators so os.path.join works correctly on Windows
    file_path = os.path.normpath(os.path.join(static_dir, file_name))
    # Create every parent directory that doesn't yet exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as fh:
        fh.write(file_bytes)

    # Return a URL with forward slashes regardless of OS
    url_path = file_name.replace(os.sep, "/")
    return f"http://localhost:{Config.PORT}/static/uploads/{url_path}"


def upload_to_storage(file_bytes: bytes, file_name: str,
                      bucket_name: str = "taskhub") -> str:
    """
    Uploads *file_bytes* to Supabase Storage under *bucket_name*/*file_name*.
    Falls back to local storage if SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are
    not configured.

    Returns the public URL of the uploaded file.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    # Storage uploads require a service-role key, not the anon/publishable key.
    # Prefer SUPABASE_SERVICE_ROLE_KEY; fall back to SUPABASE_KEY only if it
    # doesn't look like a publishable key (publishable keys start with 'sb_publishable').
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.environ.get("SUPABASE_KEY", "")
    supabase_key = service_role_key or (
        anon_key if not anon_key.startswith("sb_publishable") else None
    )

    if not supabase_url or not supabase_key:
        print("[storage] Missing Supabase service-role key — saving file locally.")
        return save_local_file(file_bytes, file_name)

    url = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket_name}/{file_name}"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "image/jpeg",
    }

    try:
        response = requests.post(url, headers=headers, data=file_bytes, timeout=20)
        if response.status_code == 200:
            return (
                f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket_name}/{file_name}"
            )

        print(f"[storage] Supabase upload error ({response.status_code}): "
              f"{response.text[:200]}. Attempting bucket creation...")

        # Try to create the bucket, then retry the upload
        create_url = f"{supabase_url.rstrip('/')}/storage/v1/bucket"
        requests.post(
            create_url,
            headers={
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
            },
            json={"id": bucket_name, "name": bucket_name, "public": True},
            timeout=10,
        )

        response = requests.post(url, headers=headers, data=file_bytes, timeout=20)
        if response.status_code == 200:
            return (
                f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket_name}/{file_name}"
            )

        print("[storage] Retry failed — saving locally.")
        return save_local_file(file_bytes, file_name)

    except Exception as exc:
        print(f"[storage] Supabase connection error: {exc} — saving locally.")
        return save_local_file(file_bytes, file_name)


# ---------------------------------------------------------------------------
# Pillow compositing helpers (used by worker.py for theme/creative images)
# ---------------------------------------------------------------------------

def prepare_product_overlay(transparent_png_bytes: bytes,
                             target_size: tuple[int, int] = (1024, 1024),
                             scale_factor: float = 0.6,
                             position_offset: tuple[int, int] = (0, 0)) -> Image.Image:
    """
    Resizes the transparent product image so its largest dimension equals
    ``target_size * scale_factor``, then centres it on a transparent RGBA canvas.

    Returns the canvas as a PIL Image (RGBA).
    """
    product_img = Image.open(io.BytesIO(transparent_png_bytes)).convert("RGBA")

    max_w = int(target_size[0] * scale_factor)
    max_h = int(target_size[1] * scale_factor)
    product_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    x = (target_size[0] - product_img.width) // 2 + position_offset[0]
    y = (target_size[1] - product_img.height) // 2 + position_offset[1]
    canvas.paste(product_img, (x, y), product_img)
    return canvas


def composite_product_on_background(background_bytes: bytes,
                                     product_canvas_img: Image.Image,
                                     add_shadow: bool = True,
                                     add_reflection: bool = False) -> bytes:
    """
    Composites *product_canvas_img* (RGBA PIL Image) over *background_bytes*.

    Optionally adds:
      - A Gaussian-blurred drop shadow beneath the product.
      - A vertically-flipped, faded reflection below the product.

    Returns JPEG bytes at quality=90.
    """
    from PIL import ImageFilter

    bg_img = Image.open(io.BytesIO(background_bytes)).convert("RGBA")
    target_size = bg_img.size

    if add_reflection:
        try:
            reflected = product_canvas_img.transpose(Image.FLIP_TOP_BOTTOM)
            r, g, b, alpha = reflected.split()
            alpha_data = bytearray(alpha.tobytes())
            width, height = target_size
            for y in range(height):
                factor = 0.15 * (1.0 - (y / height))
                for x in range(width):
                    idx = y * width + x
                    alpha_data[idx] = int(alpha_data[idx] * factor)
            faded_alpha = Image.frombytes("L", target_size, bytes(alpha_data))
            reflected_faded = Image.merge("RGBA", (r, g, b, faded_alpha))
            reflection_offset = int(target_size[1] * 0.05)
            reflection_canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
            reflection_canvas.paste(reflected_faded, (0, reflection_offset), reflected_faded)
            bg_img = Image.alpha_composite(bg_img, reflection_canvas)
        except Exception as exc:
            print(f"[composite] Reflection generation failed: {exc}")

    if add_shadow:
        try:
            alpha = product_canvas_img.split()[3]
            shadow_color = Image.new("RGBA", target_size, (15, 15, 15, 255))
            shadow = Image.new("RGBA", target_size, (0, 0, 0, 0))
            shadow.paste(shadow_color, (0, 0), alpha)
            shadow_blurred = shadow.filter(ImageFilter.GaussianBlur(radius=15))
            shadow_offset = (int(target_size[0] * 0.01), int(target_size[1] * 0.02))
            shadow_canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
            shadow_canvas.paste(shadow_blurred, shadow_offset, shadow_blurred)
            bg_img = Image.alpha_composite(bg_img, shadow_canvas)
        except Exception as exc:
            print(f"[composite] Shadow generation failed: {exc}")

    bg_img = Image.alpha_composite(bg_img, product_canvas_img)

    out = io.BytesIO()
    bg_img.convert("RGB").save(out, format="JPEG", quality=90)
    return out.getvalue()
