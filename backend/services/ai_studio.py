import io
import os
import uuid
import requests
from PIL import Image
import replicate
from google import genai
from google.genai import types
from config import Config

def save_local_file(file_bytes, file_name):
    """
    Saves a file locally to the static/uploads folder as a fallback.
    """
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
    os.makedirs(static_dir, exist_ok=True)
    
    file_path = os.path.join(static_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
        
    return f"http://localhost:{Config.PORT}/static/uploads/{file_name}"

def upload_to_storage(file_bytes, file_name, bucket_name="taskhub"):
    """
    Uploads file bytes to Supabase Storage, falling back to local storage if keys are missing.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Missing Supabase configuration. Saving file locally.")
        return save_local_file(file_bytes, file_name)
        
    url = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket_name}/{file_name}"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "image/png"
    }
    
    try:
        response = requests.post(url, headers=headers, data=file_bytes, timeout=15)
        if response.status_code == 200:
            return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket_name}/{file_name}"
        else:
            print(f"Supabase storage upload error: {response.text}. Retrying with bucket creation...")
            
            create_bucket_url = f"{supabase_url.rstrip('/')}/storage/v1/bucket"
            bucket_headers = {
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json"
            }
            requests.post(create_bucket_url, headers=bucket_headers, json={
                "id": bucket_name,
                "name": bucket_name,
                "public": True
            }, timeout=5)
            
            response = requests.post(url, headers=headers, data=file_bytes, timeout=15)
            if response.status_code == 200:
                return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket_name}/{file_name}"
            
            print(f"Supabase storage upload retry failed. Saving locally.")
            return save_local_file(file_bytes, file_name)
    except Exception as e:
        print(f"Supabase storage connection error: {str(e)}. Saving locally.")
        return save_local_file(file_bytes, file_name)

def extract_product_background(image_bytes):
    """
    Removes the background from the product image.
    Uses Replicate API's lucataco/remove-bg if REPLICATE_API_TOKEN is present.
    Otherwise, falls back to the color-keying transparency fallback.
    """
    if Config.REPLICATE_API_TOKEN:
        try:
            temp_name = f"temp_remove_bg_{uuid.uuid4()}.png"
            temp_url = upload_to_storage(image_bytes, temp_name)
            
            print(f"Calling Replicate to remove background for {temp_url}...")
            
            output = replicate.Client(api_token=Config.REPLICATE_API_TOKEN).run(
                "lucataco/remove-bg:95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1",
                input={"image": temp_url}
            )
            
            response = requests.get(output, timeout=15)
            if response.status_code == 200:
                print("Replicate background removal succeeded.")
                return response.content
            else:
                print(f"Failed to download Replicate remove-bg result: {response.text}")
        except Exception as e:
            print(f"Replicate remove-bg API call failed: {str(e)}")
            
    print("Executing fallback white-color keying background removal locally.")
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        datas = img.getdata()
        
        new_data = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as ex:
        print(f"Fallback background removal failed: {str(ex)}")
        return image_bytes

def prepare_product_overlay(transparent_png_bytes, target_size=(1024, 1024), scale_factor=0.6, position_offset=(0, 0)):
    """
    Resizes the transparent product image and places it centered on a transparent canvas of target_size.
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

def generate_background_scene(prompt, aspect_ratio="1:1"):
    """
    Generates a background scene using Google Gemini Imagen model.
    """
    gemini_key = Config.GEMINI_API_KEY
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is not configured in environment variables.")
        
    print(f"Generating background via Gemini Imagen: {prompt[:100]}...")
    
    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_images(
        model='imagen-3.0-generate-001',
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            output_mime_type='image/png'
        )
    )
    
    if not response.generated_images:
        raise ValueError("Failed to generate background scene from Gemini API.")
        
    return response.generated_images[0].image.image_bytes

def composite_product_on_background(background_bytes, product_canvas_img, add_shadow=True, add_reflection=False):
    """
    Composites the transparent product canvas image on top of the generated background image.
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
        except Exception as e:
            print(f"Failed to generate reflection: {str(e)}")
            
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
        except Exception as e:
            print(f"Failed to generate drop shadow: {str(e)}")
            
    bg_img = Image.alpha_composite(bg_img, product_canvas_img)
    
    out_io = io.BytesIO()
    bg_img.convert("RGB").save(out_io, format="JPEG", quality=90)
    return out_io.getvalue()

def get_generation_prompts(product_title, product_description, image_type, angle=None):
    """
    Constructs detailed environment prompts for Gemini API based on product title/category.
    Uses DNA prompting to generate a photo-realistic, consistent human model.
    """
    title = (product_title or "").lower()
    
    category = "general"
    if "ring" in title or "band" in title:
        category = "ring"
    elif "earring" in title or "stud" in title:
        category = "earring"
    elif "necklace" in title or "pendant" in title or "chain" in title:
        category = "necklace"
    elif "bracelet" in title or "bangle" in title or "watch" in title:
        category = "bracelet"
        
    model_dna = "A 28-year-old female model with Hazel eyes, symmetrical facial features, dark brown shoulder-length wavy hair, natural skin texture, soft daylight studio lighting, wearing a simple elegant black silk scoop-neck top"
    
    prompts = {}
    
    prompts["white_background"] = {
        "prompt": "A solid, clean, pure white (#FFFFFF) photography studio background, soft professional studio lighting, minimalist composition, 8k",
        "negative_prompt": "shadows, objects, scenes"
    }
    
    prompts["theme_1"] = {
        "prompt": "A luxury, clean, white marble tabletop, soft natural window light reflections on the polished surface, elegant bokeh, blurred warm neutral room interior background, professional catalog photography, 8k",
        "negative_prompt": "dark, objects, text"
    }
    
    prompts["theme_2"] = {
        "prompt": "A rich dark black velvet cloth drape with elegant soft folds resting on a surface, dramatic side spotlighting, deep shadows, professional luxury studio setup, 8k",
        "negative_prompt": "bright, color, text"
    }
    
    prompts["creative_1"] = {
        "prompt": "A flat, dark sea rock on a sandy beach, warm golden hour sunset lighting, soft ocean wave spray and sea foam in the blurred background, cinematic lighting, 8k",
        "negative_prompt": "model, person, hands, skin"
    }
    
    prompts["creative_2"] = {
        "prompt": "A modern, sleek matte black pedestal in a dark studio, surrounded by glossy dark tropical palm leaves, soft cyan and magenta neon light accents, high contrast, cinematic atmosphere, 8k",
        "negative_prompt": "model, person, skin"
    }
    
    if category == "ring":
        prompts["model_front"] = {
            "prompt": "A close-up photograph of a model's hand with elegant manicured nails resting gently on a soft white linen surface, soft natural side lighting, detailed skin texture, 8k, fashion catalog background",
            "negative_prompt": "ugly hands, deformed fingers, low quality, jewelry, ring, metal"
        }
        prompts["model_side"] = {
            "prompt": "A close-up photograph of a model's hand with elegant manicured nails resting on a white marble table, showing a 45-degree angle of the fingers, soft daylight, 8k",
            "negative_prompt": "deformed fingers, jewelry, ring"
        }
        prompts["model_close"] = {
            "prompt": "An extreme macro detail shot of a model's hand fingers, soft focus, warm studio lighting, clean background, 8k",
            "negative_prompt": "deformed fingers, jewelry, ring"
        }
    elif category == "earring":
        prompts["model_front"] = {
            "prompt": f"A close-up front view portrait focusing on the ear and neck of {model_dna}, showing soft skin texture, soft studio side lighting, clean neutral gray background, 8k",
            "negative_prompt": "jewelry, earring, metal, deformed ear"
        }
        prompts["model_side"] = {
            "prompt": f"A close-up profile view portrait showing the side of the face and ear of {model_dna}, showing soft skin texture, warm side lighting, clean neutral background, 8k",
            "negative_prompt": "jewelry, earring, metal, deformed ear"
        }
        prompts["model_close"] = {
            "prompt": f"An extreme macro close-up photograph of the ear lobe of {model_dna}, soft skin tone, cinematic studio lighting, detailed pores, 8k",
            "negative_prompt": "jewelry, earring, metal, deformed ear"
        }
    elif category == "necklace":
        prompts["model_front"] = {
            "prompt": f"A close-up front photograph of the neck and collarbone of {model_dna}, wearing an elegant black scoop-neck silk top, soft window daylight, clean studio background, 8k",
            "negative_prompt": "jewelry, necklace, chain, pendant, hands"
        }
        prompts["model_side"] = {
            "prompt": f"A close-up profile portrait showing the neck and shoulder of {model_dna}, showing collarbone details, wearing a black silk scoop-neck top, soft studio lighting, 8k",
            "negative_prompt": "jewelry, necklace, chain, pendant, hands"
        }
        prompts["model_close"] = {
            "prompt": f"An extreme macro close-up view of the collarbone and neck of {model_dna}, soft focus, warm daylight reflections on skin, 8k",
            "negative_prompt": "jewelry, necklace, chain, pendant, hands"
        }
    else:
        prompts["model_front"] = {
            "prompt": f"A close-up portrait of {model_dna}'s wrist and hand resting gently on a black silk surface, soft daylight studio lighting, clean catalog style, 8k",
            "negative_prompt": "jewelry, bracelet, watch"
        }
        prompts["model_side"] = {
            "prompt": f"A close-up photograph of the forearm and wrist of {model_dna} resting on a wooden table, 45-degree angle, soft side lighting, 8k",
            "negative_prompt": "jewelry, bracelet, watch"
        }
        prompts["model_close"] = {
            "prompt": f"An extreme macro close-up photograph of the wrist area of {model_dna}, soft skin tones, cinematic lighting, 8k",
            "negative_prompt": "jewelry, bracelet, watch"
        }
        
    if image_type.startswith("model_") and angle:
        key = f"model_{angle}"
        if key in prompts:
            return prompts[key]
            
    return prompts.get(image_type, prompts["white_background"])
