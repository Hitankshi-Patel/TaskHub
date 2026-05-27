from __future__ import annotations

import io
import os
import requests
from PIL import Image
from config import Config


def save_local_file(file_bytes: bytes, file_name: str) -> str:
    static_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static", "uploads"
    )
    file_path = os.path.normpath(os.path.join(static_dir, file_name))
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as fh:
        fh.write(file_bytes)

    url_path = file_name.replace(os.sep, "/")
    return f"http://localhost:{Config.PORT}/static/uploads/{url_path}"


def upload_to_storage(file_bytes: bytes, file_name: str,
                      bucket_name: str = "taskhub") -> str:
    supabase_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.environ.get("SUPABASE_KEY", "")
    supabase_key = service_role_key or (
        anon_key if not anon_key.startswith("sb_publishable") else None
    )

    if not supabase_url or not supabase_key:
        print("[storage] Missing Supabase credentials — saving locally.")
        return save_local_file(file_bytes, file_name)

    url = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket_name}/{file_name}"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "image/jpeg",
    }

    try:
        response = requests.post(url, headers=headers, data=file_bytes, timeout=20)
        if response.status_code == 200:
            return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket_name}/{file_name}"

        print(f"[storage] Upload error ({response.status_code}): {response.text[:200]}. Trying bucket creation...")

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
            return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket_name}/{file_name}"

        print("[storage] Retry failed — saving locally.")
        return save_local_file(file_bytes, file_name)

    except Exception as exc:
        print(f"[storage] Connection error: {exc} — saving locally.")
        return save_local_file(file_bytes, file_name)


def prepare_product_overlay(transparent_png_bytes: bytes,
                             target_size: tuple[int, int] = (1024, 1024),
                             scale_factor: float = 0.6,
                             position_offset: tuple[int, int] = (0, 0)) -> Image.Image:
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
            print(f"[composite] Reflection failed: {exc}")

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
            print(f"[composite] Shadow failed: {exc}")

    bg_img = Image.alpha_composite(bg_img, product_canvas_img)

    out = io.BytesIO()
    bg_img.convert("RGB").save(out, format="JPEG", quality=90)
    return out.getvalue()
