import io
import os
import uuid
import requests
from PIL import Image
import replicate
from ..config import Config

# Initialize Replicate client if token is present
replicate_client = None
if Config.REPLICATE_API_TOKEN:
    # Use client with specific token
    replicate_client = replicate.Client(api_token=Config.REPLICATE_API_TOKEN)

def save_local_file(file_bytes, file_name):
    """
    Saves a file locally to the static/uploads folder as a fallback.
    """
    # Create static/uploads directory
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
    os.makedirs(static_dir, exist_ok=True)
    
    file_path = os.path.join(static_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
        
    # Return local relative/absolute URL
    # In Flask we will serve the static files, so we can return /static/uploads/file_name
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
        # Try uploading to Supabase Storage
        response = requests.post(url, headers=headers, data=file_bytes, timeout=15)
        if response.status_code == 200:
            return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket_name}/{file_name}"
        else:
            print(f"Supabase storage upload error: {response.text}. Retrying with bucket creation...")
            
            # Try to create bucket if it doesn't exist (Supabase Storage Admin API)
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
            
            # Retry upload
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
    Removes the background from the product image using rembg locally.
    Returns the transparent PNG bytes.
    """
    try:
        from rembg import remove
        
        # Load image into PIL
        input_image = Image.open(io.BytesIO(image_bytes))
        
        # Run background removal
        output_image = remove(input_image)
        
        # Save output image to bytes
        img_byte_arr = io.BytesIO()
        output_image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
        
    except Exception as e:
        print(f"Local rembg failed or not installed: {str(e)}. Executing fallback background removal.")
        # Fallback: Create transparency by setting white pixels to transparent
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            datas = img.getdata()
            
            new_data = []
            for item in datas:
                # If pixels are very bright (almost white), make them transparent
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

def prepare_inpainting_assets(transparent_png_bytes):
    """
    Prepares base image and mask for inpainting.
    The mask will have white (255) pixels for background and black (0) for product.
    Returns (base_image_bytes, mask_bytes).
    """
    product_img = Image.open(io.BytesIO(transparent_png_bytes)).convert("RGBA")
    
    # Standardize image size to 768x768 or 1024x1024 for SDXL
    target_size = (768, 768)
    
    # Calculate aspect ratio preserving resize
    product_img.thumbnail((target_size[0] - 100, target_size[1] - 100), Image.Resampling.LANCZOS)
    
    # Create canvas and center product
    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    offset = ((target_size[0] - product_img.width) // 2, (target_size[1] - product_img.height) // 2)
    canvas.paste(product_img, offset, product_img)
    
    # Generate mask: White (255) where transparent, Black (0) where opaque
    alpha = canvas.split()[3]
    mask = Image.eval(alpha, lambda a: 255 if a == 0 else 0)
    
    # Base Image: Paste product on top of solid gray canvas (helps SDXL context)
    base = Image.new("RGB", target_size, (128, 128, 128))
    base.paste(canvas, (0, 0), canvas)
    
    # Save base to bytes
    base_io = io.BytesIO()
    base.save(base_io, format="PNG")
    
    # Save mask to bytes
    mask_io = io.BytesIO()
    mask.save(mask_io, format="PNG")
    
    return base_io.getvalue(), mask_io.getvalue()

def get_generation_prompts(product_description, image_type, angle=None):
    """
    Constructs detailed inpainting prompts based on the image type and description.
    """
    desc = product_description or "jewelry item"
    
    # Prompts dictionary
    prompts = {
        "white_background": {
            "prompt": f"A professional e-commerce product photograph of {desc}, centered, on a solid clean pure white (#FFFFFF) background, soft studio lighting, soft shadows beneath the product, crisp focus, 8k, DSLR photography",
            "negative_prompt": "model, person, hands, skin, background scene, patterns, dark background, blurry, bad anatomy, text, watermark, logo"
        },
        "theme_1": {
            "prompt": f"A luxury DSLR product photo of {desc} resting elegantly on a polished white marble surface, soft side window lighting, elegant reflections, shallow depth of field, 8k, professional branding photography",
            "negative_prompt": "cartoon, illustration, sketch, low quality, model, human body, hands, text, blurry, distorted"
        },
        "theme_2": {
            "prompt": f"A professional commercial product photo of {desc} laying on a rich dark velvet cloth background, dramatic single-source spotlight, deep shadows, high-end jewelry styling, 8k, DSLR",
            "negative_prompt": "cartoon, low quality, drawing, model, hands, skin, text, watermark, blurry"
        },
        "creative_1": {
            "prompt": f"A creative lifestyle product photograph of {desc} placed on a flat sea-rock at a beautiful beach during a golden sunset, soft ocean wave spray in the background, warm light reflections on the metal, photorealistic, 8k",
            "negative_prompt": "model, human, hands, cartoon, low quality, noise, text, watermark, drawing"
        },
        "creative_2": {
            "prompt": f"A stunning artistic studio photograph of {desc} positioned on a sleek black pedestal, surrounded by elegant glossy tropical palm leaves, neon cyan and magenta accents, high contrast, cinematic, DSLR",
            "negative_prompt": "model, person, skin, cartoon, low quality, flat lighting, text, watermark"
        },
        "model_front": {
            "prompt": f"A hyperrealistic professional fashion model wearing {desc}, front view, natural skin texture, elegant pose, clean studio setting, high-end catalog photography, soft focus, 8k, DSLR",
            "negative_prompt": "ugly, deformed, extra limbs, bad skin, cartoon, anime, low resolution, text, watermark, drawing"
        },
        "model_side": {
            "prompt": f"A high-fashion profile portrait of a model wearing {desc}, side view, 45-degree angle, sharp focus on the jewelry details, natural lighting, luxury fashion editorial, 8k, DSLR",
            "negative_prompt": "deformed, extra limbs, ugly, bad skin, cartoon, low quality, text, watermark"
        },
        "model_close": {
            "prompt": f"An extreme close-up detail shot of {desc} worn by a professional model, showcasing the fine details and craftsmanship, soft skin tones, high-end commercial fashion advertisement, 8k, DSLR",
            "negative_prompt": "ugly, deformed, extra limbs, bad skin, cartoon, low resolution, text, watermark"
        }
    }
    
    # Specific adjustment for angle override
    if image_type.startswith("model_") and angle:
        key = f"model_{angle}"
        if key in prompts:
            return prompts[key]
            
    return prompts.get(image_type, prompts["white_background"])

def generate_inpaint_image(base_url, mask_url, prompt, negative_prompt):
    """
    Submits inpainting job to Replicate using the SDXL Inpaint model.
    """
    if not Config.REPLICATE_API_TOKEN:
        raise ValueError("Replicate API Token is not configured in environment variables.")
        
    print(f"Submitting to Replicate: {prompt[:50]}...")
    
    # Submit job using the Replicate client
    # The sepal/sdxl-inpainting model takes base image, mask, prompt, negative_prompt
    output = replicate.Client(api_token=Config.REPLICATE_API_TOKEN).run(
        Config.REPLICATE_INPAINT_MODEL,
        input={
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image": base_url,
            "mask": mask_url,
            "num_inference_steps": 40,
            "guidance_scale": 7.5,
            "strength": 0.95
        }
    )
    
    # Return output image URL (output is usually a list of URLs or a single URL)
    if isinstance(output, list) and len(output) > 0:
        return output[0]
    return output
