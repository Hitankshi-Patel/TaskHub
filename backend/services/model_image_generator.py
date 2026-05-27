from __future__ import annotations

import base64
import io
import os
import time

from google import genai
from google.genai import types
from PIL import Image

from config import Config


FALLBACK_JEWELRY_DESCRIPTION = (
    "a multi-strand pearl necklace featuring five strands of cream-white 8mm "
    "freshwater pearls, secured with an ornate 22-karat gold box clasp featuring "
    "a floral filigree design, the strands graduating slightly in length so they "
    "drape naturally against the collarbone and upper chest, the pearls have a "
    "soft rose-pink overtone and high lustre with visible surface texture"
)

_FREE_TIER_SLEEP_SECONDS = 35
_GEMINI_MODEL = "gemini-3.1-flash-image-preview"


def get_front_view_prompt(jewelry_description: str) -> str:
    return (
        "Generate a single photorealistic professional fashion photography image. "
        "Do not generate multiple images. Do not add any text overlays or watermarks.\n\n"
        "Subject: A young South Asian woman in her mid-twenties. She is standing "
        "directly facing the camera with a relaxed posture, both hands resting "
        "naturally at her sides, and a soft confident smile. Her facial features "
        "are symmetrical and natural. Her skin has visible natural texture including "
        "pores — no smoothing or retouching effect. She is wearing "
        f"{jewelry_description}. "
        "The jewelry is the hero product of this image and must be razor sharp, "
        "fully detailed, and prominently visible against her collarbone.\n\n"
        "Setting: Minimalist professional photography studio. Seamless light grey "
        "backdrop. No props, no furniture, no distractions.\n\n"
        "Camera: Simulated Canon EOS R5 body with 85mm f/1.8 prime lens. Subject "
        "fills approximately 70 percent of the frame vertically. Eye-level shooting "
        "angle. Shallow depth of field with the background softly blurred while the "
        "subject and jewelry remain in sharp focus.\n\n"
        "Lighting: Three-point studio lighting setup. Large octabox as the key light "
        "positioned 45 degrees to her left providing soft diffused illumination. "
        "Secondary fill light on her right at approximately 30 percent intensity "
        "to soften shadows. Rim light positioned behind and slightly above her "
        "creating a subtle luminous separation from the backdrop. No harsh shadows "
        "on face. Natural catchlights visible in both eyes.\n\n"
        "Quality requirements: This image must be completely indistinguishable from "
        "a real photograph taken in a professional studio. Skin pores visible. "
        "Hair strands individually rendered. Jewelry surface texture, lustre, and "
        "material properties must be photorealistic. No AI artifacts. No distorted "
        "fingers or hands. No plastic skin. No over-sharpening. The final result "
        "must meet the standard of a luxury jewelry magazine editorial photograph."
    )


def get_side_view_prompt(jewelry_description: str) -> str:
    return (
        "Generate a single photorealistic professional fashion photography image. "
        "Do not generate multiple images. Do not add any text overlays or watermarks.\n\n"
        "IMPORTANT: A reference image of the model is attached. You must use the "
        "exact same model from the reference image — same face, same skin tone, "
        "same age, same hair, same body type. Only the pose and angle change.\n\n"
        "Subject: The same South Asian woman from the reference image. Her body "
        "is now rotated 45 degrees to the left so her left shoulder is closer to "
        "the camera and her right shoulder recedes naturally into the background. "
        "Her face is turned slightly back toward the camera showing a three-quarter "
        "profile view with her chin tilted slightly downward. Her expression is "
        "relaxed and natural. She is wearing "
        f"{jewelry_description}. "
        "From this 45-degree angle the jewelry drapes naturally and must remain in "
        "sharp focus with every detail — strand layering, clasp position, pearl lustre — "
        "clearly visible. The jewelry must look identical in every detail to how "
        "it appeared in the reference image.\n\n"
        "Setting: Identical minimalist studio to the reference image. Same seamless "
        "light grey backdrop. Continuous and consistent with the front view setting.\n\n"
        "Camera: Same simulated Canon EOS R5 with 85mm f/1.8. Eye-level angle. "
        "Three-quarter body frame. Shallow depth of field.\n\n"
        "Lighting: Same three-point setup as the reference image. The rim light "
        "is now more prominently visible along the far right shoulder edge creating "
        "strong separation from the backdrop. The key light sculpts the cheekbone "
        "from the front-facing side naturally.\n\n"
        "Quality requirements: Identical standard to the reference image. Skin "
        "pores visible. Natural hair rendering. Jewelry photorealistic. No AI "
        "artifacts. No distorted anatomy. The final image must look like the next "
        "shot in the same editorial photoshoot as the reference image."
    )


def get_closeup_prompt(jewelry_description: str) -> str:
    return (
        "Generate a single photorealistic extreme close-up commercial jewelry "
        "photography image. Do not generate multiple images. Do not add any text "
        "overlays or watermarks.\n\n"
        "IMPORTANT: A reference image of the model is attached. You must use the "
        "exact same model from the reference image — same face, same skin tone, "
        "same age, same hair. Only the framing and focus change.\n\n"
        "Framing: The frame captures from the model's mid-chest area to just above "
        "the top of her head. This is a tight close-up — not a full body shot. "
        "The model's face appears in the soft upper third of the frame. The jewelry "
        "occupies the center and lower center of the frame and is the absolute "
        "focal point.\n\n"
        "Subject: The same South Asian woman from the reference image with a calm "
        "and natural expression. She is wearing "
        f"{jewelry_description}. "
        "Every single element of the jewelry must be rendered with extreme "
        "photorealistic detail — individual pearl surface texture, soft rose-pink "
        "overtone lustre, the filigree detail on the gold clasp, the way the "
        "strands layer and graduate against her skin. This image must look like it "
        "belongs in a Tanishq or Malabar Gold premium product advertisement.\n\n"
        "Background: Completely smooth bokeh blur — the background is an "
        "out-of-focus gradient of grey with zero discernible detail.\n\n"
        "Camera: Simulated Canon EOS R5 with 135mm f/2.0 telephoto lens. "
        "The compression from the longer focal length creates a flattering "
        "perspective. Macro-adjacent framing. Only the jewelry and the immediate "
        "skin area around it are in sharp focus. The face above is slightly soft "
        "but fully recognizable as the same model.\n\n"
        "Lighting: Beauty dish as the primary key light positioned directly above "
        "the camera axis providing even, flattering illumination. A small dedicated "
        "specular highlight source is directed specifically at the jewelry to bring "
        "out the pearl lustre and gold clasp reflectivity. Catchlights visible in "
        "both eyes even in this close-up frame.\n\n"
        "Quality requirements: Hyper-realistic commercial photography standard. "
        "Individual pearl texture visible. Gold metal grain and reflection accurate. "
        "Natural skin texture on chest and neck — no smoothing. No AI artifacts. "
        "No distortion. This image must be indistinguishable from a photograph "
        "taken by a professional commercial jewelry photographer."
    )


class ModelImageGenerator:
    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY") or Config.GEMINI_API_KEY
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com."
            )
        self._client = genai.Client(api_key=api_key)

    def generate_all_three(
        self,
        task_id: str,
        jewelry_description: str,
        product_image_bytes: bytes | None = None,
    ) -> dict[str, bytes]:
        from services.ai_studio import upload_to_storage

        desc = jewelry_description.strip() if jewelry_description else FALLBACK_JEWELRY_DESCRIPTION

        print(f"[Gemini] Generating model_front for task {task_id}...")
        front_bytes = self.generate_front_view(desc, product_image_bytes)
        _upload(front_bytes, task_id, "front", upload_to_storage)

        print(f"[Gemini] Sleeping {_FREE_TIER_SLEEP_SECONDS}s (free-tier rate limit)...")
        time.sleep(_FREE_TIER_SLEEP_SECONDS)

        print(f"[Gemini] Generating model_side for task {task_id}...")
        side_bytes = self.generate_side_view(desc, front_bytes, product_image_bytes)
        _upload(side_bytes, task_id, "side", upload_to_storage)

        print(f"[Gemini] Sleeping {_FREE_TIER_SLEEP_SECONDS}s (free-tier rate limit)...")
        time.sleep(_FREE_TIER_SLEEP_SECONDS)

        print(f"[Gemini] Generating model_closeup for task {task_id}...")
        closeup_bytes = self.generate_closeup(desc, front_bytes, product_image_bytes)
        _upload(closeup_bytes, task_id, "closeup", upload_to_storage)

        print(f"[Gemini] All three model images complete for task {task_id}.")
        return {"front": front_bytes, "side": side_bytes, "closeup": closeup_bytes}

    def generate_front_view(
        self,
        jewelry_description: str,
        product_image_bytes: bytes | None = None,
    ) -> bytes:
        parts: list = [get_front_view_prompt(jewelry_description)]
        if product_image_bytes:
            parts.append(_make_part(product_image_bytes))
        return self._call_gemini(parts)

    def generate_side_view(
        self,
        jewelry_description: str,
        anchor_image_bytes: bytes,
        product_image_bytes: bytes | None = None,
    ) -> bytes:
        parts: list = [
            get_side_view_prompt(jewelry_description),
            _make_part(anchor_image_bytes),
        ]
        if product_image_bytes:
            parts.append(_make_part(product_image_bytes))
        return self._call_gemini(parts)

    def generate_closeup(
        self,
        jewelry_description: str,
        anchor_image_bytes: bytes,
        product_image_bytes: bytes | None = None,
    ) -> bytes:
        parts: list = [
            get_closeup_prompt(jewelry_description),
            _make_part(anchor_image_bytes),
        ]
        if product_image_bytes:
            parts.append(_make_part(product_image_bytes))
        return self._call_gemini(parts)

    def _call_gemini(self, parts: list) -> bytes:
        try:
            response = self._client.models.generate_content(
                model=_GEMINI_MODEL,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )
        except Exception as exc:
            raise RuntimeError(f"Gemini API call failed: {exc}") from exc

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data is not None:
                    raw_bytes = base64.b64decode(part.inline_data.data)
                    return _ensure_png(raw_bytes)

        finish_reason = (
            response.candidates[0].finish_reason
            if response.candidates else "unknown"
        )
        raise ValueError(
            f"Gemini returned no image. Finish reason: {finish_reason}"
        )


def _make_part(image_bytes: bytes) -> types.Part:
    if image_bytes[:4] == b"\x89PNG":
        mime = "image/png"
    elif image_bytes[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    else:
        mime = "image/png"
    return types.Part.from_bytes(data=image_bytes, mime_type=mime)


def _ensure_png(raw_bytes: bytes) -> bytes:
    if raw_bytes[:4] == b"\x89PNG":
        return raw_bytes
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return raw_bytes


def _upload(image_bytes: bytes, task_id: str, angle: str, upload_fn) -> str:
    storage_path = f"tasks/{task_id}/model_{angle}.png"
    print(f"[Gemini] Uploading {storage_path}...")
    url = upload_fn(image_bytes, storage_path)
    print(f"[Gemini] Uploaded → {url}")
    return url
