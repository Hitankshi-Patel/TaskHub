"""
image_pipeline.py
=================
Image generation pipeline for TaskHub.

Strategy per image type:
  white_background  → pure Pillow composite on #FFFFFF canvas
  theme_1 (marble)  → Unsplash real photo + Pillow composite
  theme_2 (velvet)  → Unsplash real photo + Pillow composite
  creative_1 (beach)  → Unsplash real photo + Pillow composite (bg blur)
  creative_2 (floral) → Unsplash real photo + Pillow composite (bg blur)
  model_front / model_side / model_close
                    → Google Gemini 2.5 Flash Image (free tier)
                      handled by services/model_image_generator.py

Foundation for all 8:
  rembg runs locally (ONNX, free) to extract a transparent product PNG.
  The result is cached to disk (path stored on Task.rembg_cache_path)
  so ONNX inference only runs ONCE per task.
"""

from __future__ import annotations

import io
import os
import uuid
import requests
from PIL import Image, ImageFilter
from config import Config

# ---------------------------------------------------------------------------
# Unsplash search queries for each image type
# ---------------------------------------------------------------------------
UNSPLASH_QUERIES = {
    "theme_1":    "white marble luxury surface flat lay",
    "theme_2":    "dark navy velvet fabric texture product photography",
    "creative_1": "golden hour beach sunset bokeh lifestyle photography",
    "creative_2": "rose garden soft bokeh editorial fashion photography",
}

# ---------------------------------------------------------------------------
# Step 0 — rembg background removal (local, free)
# ---------------------------------------------------------------------------

def extract_with_rembg(image_bytes: bytes) -> bytes:
    """
    Removes the background from *image_bytes* using the U2Net ONNX model via
    onnxruntime — identical to what rembg does internally, but without the
    pymatting/numba chain that can crash in certain Anaconda environments.

    The U2Net model file (~176 MB) is downloaded once to the OS cache directory
    on first call and reused on subsequent calls.

    Returns transparent RGBA PNG bytes.
    Falls back to white-pixel colour-keying if onnxruntime inference fails.
    """
    try:
        import numpy as np
        import onnxruntime as ort

        # ---- download / locate the U2Net ONNX model ----
        # Use /tmp on read-only filesystems (e.g. Vercel), fall back to ~/.u2net
        import os, hashlib, urllib.request
        _home_cache = os.path.join(os.path.expanduser("~"), ".u2net")
        try:
            os.makedirs(_home_cache, exist_ok=True)
            cache_dir = _home_cache
        except OSError:
            cache_dir = "/tmp/.u2net"
            os.makedirs(cache_dir, exist_ok=True)
        model_path = os.path.join(cache_dir, "u2net.onnx")

        if not os.path.exists(model_path):
            model_url = (
                "https://github.com/danielgatis/rembg/releases/download/"
                "v0.0.0/u2net.onnx"
            )
            print(f"[rembg] Downloading U2Net ONNX model (~176 MB) to {model_path}...")
            urllib.request.urlretrieve(model_url, model_path)
            print("[rembg] Model download complete.")

        # ---- pre-process ----
        input_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        orig_size = input_img.size  # (W, H)

        resized = input_img.resize((320, 320), Image.Resampling.BILINEAR)
        img_np = np.array(resized, dtype=np.float32) / 255.0
        # Normalize with ImageNet mean/std (same as rembg)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img_np = (img_np - mean) / std
        # HWC → CHW → NCHW
        img_np = img_np.transpose(2, 0, 1)[np.newaxis, ...]

        # ---- inference ----
        print("[rembg] Running U2Net ONNX inference...")
        sess_opts = ort.SessionOptions()
        sess_opts.log_severity_level = 3  # suppress verbose ONNX logs
        session = ort.InferenceSession(
            model_path,
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        input_name = session.get_inputs()[0].name
        raw_output = session.run(None, {input_name: img_np})[0]  # shape (1,1,320,320)
        print("[rembg] Inference complete.")

        # ---- post-process: build alpha mask ----
        mask = raw_output[0, 0]  # (320, 320)
        # Normalize to [0, 1]
        mask = (mask - mask.min()) / (mask.max() - mask.min() + 1e-8)
        mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
        mask_img = mask_img.resize(orig_size, Image.Resampling.LANCZOS)

        # Combine original RGB with alpha mask
        rgba = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        rgba.putalpha(mask_img)

        out = io.BytesIO()
        rgba.save(out, format="PNG")
        print("[rembg] Transparent PNG ready.")
        return out.getvalue()

    except Exception as exc:
        print(f"[rembg] U2Net ONNX inference failed ({exc}) — falling back to colour-key removal.")

    # Fallback: naive white-colour keying
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    new_data = []
    for pixel in img.getdata():
        r, g, b, a = pixel
        # Make white-ish pixels transparent
        if r > 240 and g > 240 and b > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(pixel)
    img.putdata(new_data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_or_create_rembg_cache(task, original_bytes: bytes) -> bytes:
    """
    Reads the cached rembg PNG from disk if it exists, otherwise runs rembg,
    writes the result to disk, and persists the path on *task*.

    This ensures ONNX inference runs at most once per task regardless of how many
    of the 8 image types are generated.
    """
    from models import db

    # If already cached and the file still exists, read and return it
    if task.rembg_cache_path and os.path.exists(task.rembg_cache_path):
        print(f"[rembg] Using cached transparent PNG: {task.rembg_cache_path}")
        with open(task.rembg_cache_path, "rb") as fh:
            return fh.read()

    # Run rembg
    transparent_bytes = extract_with_rembg(original_bytes)

    # Persist to /tmp/rembg_cache — the only writable dir on Vercel (read-only FS).
    # On a normal server this is still fine; files survive until the process restarts.
    cache_dir = "/tmp/rembg_cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{task.id}.png")

    with open(cache_path, "wb") as fh:
        fh.write(transparent_bytes)

    # Persist path to DB
    task.rembg_cache_path = cache_path
    db.session.commit()
    print(f"[rembg] Cached transparent PNG saved to {cache_path}")

    return transparent_bytes


# ---------------------------------------------------------------------------
# Step 1 — White background (pure Pillow, zero API)
# ---------------------------------------------------------------------------

def _make_drop_shadow(product_img: Image.Image, canvas_size: tuple[int, int],
                      offset: tuple[int, int] = (7, 7),
                      blur_radius: int = 12, opacity: float = 0.30) -> Image.Image:
    """
    Creates a blurred dark silhouette of *product_img* at *offset*, at *opacity*,
    on a transparent canvas of *canvas_size*.
    """
    shadow_color = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    alpha = product_img.split()[3]  # RGBA alpha channel

    # Dark silhouette at full opacity
    silhouette = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    dark = Image.new("RGBA", product_img.size, (20, 20, 20, 255))
    silhouette.paste(dark, (
        (canvas_size[0] - product_img.width) // 2,
        (canvas_size[1] - product_img.height) // 2,
    ), alpha)

    # Blur
    blurred = silhouette.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Apply opacity by scaling the alpha channel
    r, g, b, a = blurred.split()
    a = a.point(lambda v: int(v * opacity))
    blurred = Image.merge("RGBA", (r, g, b, a))

    # Offset canvas
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    canvas.paste(blurred, offset, blurred)
    return canvas


def _scale_product_to_canvas(transparent_png_bytes: bytes,
                              canvas_size: tuple[int, int],
                              fill_fraction: float = 0.60) -> Image.Image:
    """
    Returns the product image scaled so its largest dimension is *fill_fraction*
    of the canvas, converted to RGBA.
    """
    product = Image.open(io.BytesIO(transparent_png_bytes)).convert("RGBA")
    max_dim = int(min(canvas_size) * fill_fraction)
    product.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    return product


def _center_paste(canvas: Image.Image, product: Image.Image) -> None:
    """Pastes *product* centred on *canvas* using its alpha channel."""
    x = (canvas.width - product.width) // 2
    y = (canvas.height - product.height) // 2
    canvas.paste(product, (x, y), product)


def build_white_background(transparent_png_bytes: bytes,
                            canvas_size: tuple[int, int] = (1024, 1024)) -> bytes:
    """
    Image 1 — Pure white (#FFFFFF) background.
    Adds a subtle drop shadow then centres the product on the canvas.
    Returns JPEG bytes at quality=98.
    """
    product = _scale_product_to_canvas(transparent_png_bytes, canvas_size, fill_fraction=0.62)

    canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 255))

    # Drop shadow: 7px offset, radius 12, 30% opacity
    shadow = _make_drop_shadow(product, canvas_size, offset=(7, 7), blur_radius=12, opacity=0.30)
    canvas = Image.alpha_composite(canvas, shadow)

    _center_paste(canvas, product)

    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="JPEG", quality=98)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Steps 2–5 — Unsplash background + Pillow composite
# ---------------------------------------------------------------------------

def fetch_unsplash_background(query: str,
                               orientation: str = "landscape",
                               target_size: tuple[int, int] = (1024, 1024)) -> bytes:
    """
    Fetches a random photo from Unsplash matching *query* and returns resized
    JPEG bytes of *target_size*.

    Raises ValueError if UNSPLASH_ACCESS_KEY is not configured.
    Raises RuntimeError if the API call fails.
    """
    access_key = Config.UNSPLASH_ACCESS_KEY
    if not access_key:
        raise ValueError(
            "UNSPLASH_ACCESS_KEY is not configured. "
            "Add it to your .env file (free at https://unsplash.com/developers)."
        )

    api_url = "https://api.unsplash.com/photos/random"
    params = {
        "query": query,
        "orientation": orientation,
        "client_id": access_key,
    }

    print(f"[Unsplash] Fetching background: '{query}'")
    resp = requests.get(api_url, params=params, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Unsplash API returned {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    # Prefer 'regular' (1080px) for speed; fall back to 'full'
    photo_url = data.get("urls", {}).get("regular") or data.get("urls", {}).get("full")
    if not photo_url:
        raise RuntimeError("Unsplash response did not contain a usable image URL.")

    print(f"[Unsplash] Downloading image from {photo_url[:80]}...")
    img_resp = requests.get(photo_url, timeout=30)
    if img_resp.status_code != 200:
        raise RuntimeError(f"Failed to download Unsplash image: {img_resp.status_code}")

    # Resize to target_size (centre-crop to preserve aspect)
    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
    img = _center_crop_resize(img, target_size)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=95)
    print(f"[Unsplash] Background ready ({target_size[0]}×{target_size[1]}).")
    return out.getvalue()


def _center_crop_resize(img: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    """Crops the image to the target aspect ratio from the centre, then resizes."""
    tw, th = target_size
    iw, ih = img.size
    target_ratio = tw / th
    img_ratio = iw / ih

    if img_ratio > target_ratio:
        # Image is wider — crop sides
        new_w = int(ih * target_ratio)
        left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    elif img_ratio < target_ratio:
        # Image is taller — crop top/bottom
        new_h = int(iw / target_ratio)
        top = (ih - new_h) // 2
        img = img.crop((0, top, iw, top + new_h))

    return img.resize(target_size, Image.Resampling.LANCZOS)


def build_static_composite(bg_bytes: bytes,
                            transparent_png_bytes: bytes,
                            canvas_size: tuple[int, int] = (1024, 1024),
                            blur_bg: bool = False,
                            fill_fraction: float = 0.60) -> bytes:
    """
    Composites the product over a real photographic background.

    *blur_bg* = True applies a GaussianBlur(radius=0.8) to the background layer
    before compositing — mimics shallow depth-of-field for creative images.

    Returns JPEG bytes at quality=95.
    """
    bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
    bg = bg.resize(canvas_size, Image.Resampling.LANCZOS)

    if blur_bg:
        bg = bg.filter(ImageFilter.GaussianBlur(radius=0.8))

    product = _scale_product_to_canvas(transparent_png_bytes, canvas_size, fill_fraction)

    # Drop shadow
    shadow = _make_drop_shadow(product, canvas_size, offset=(7, 8), blur_radius=14, opacity=0.32)
    bg = Image.alpha_composite(bg, shadow)

    _center_paste(bg, product)

    out = io.BytesIO()
    bg.convert("RGB").save(out, format="JPEG", quality=95)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Steps 6–8 — Google Gemini 2.5 Flash Image model generation
# ---------------------------------------------------------------------------
# Model-wearing-jewelry image generation has been moved to:
#   services/model_image_generator.py (class ModelImageGenerator)
#
# This module now covers only Steps 1–5 (background compositing).
