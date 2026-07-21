# main.py
import json
import os
from PIL import Image
from pydantic import BaseModel, Field

# Import config details and variables from your asset builder
from config import gemini_client
from downloader import recipes_json, extract_dir, setup_assets

# 1. Run the asset setup function and fetch the image file strings
image_files = setup_assets()

# 2. Open and load recipe JSON file data
with open(recipes_json, 'r', encoding='utf-8') as file:
    recipe_data = json.load(file)  # Safe loading alternative to file.read()

print("\n--- Key-Value Pairs of the First Recipe ---")
if isinstance(recipe_data, list) and len(recipe_data) > 0:
    for key, value in recipe_data[0].items():
        print(f"{key}: {value}")
else:
    print("Recipe JSON data is empty or structurally invalid.")

# =====================================================================
# 3. FIX PLACEMENT: Check and open images cleanly by looking inside the subfolder
# =====================================================================
# =====================================================================
# 3. Check and open images cleanly (OS-forced fallback)
# =====================================================================
# =====================================================================
# 3. Check and open images cleanly (OS-forced fallback)
# =====================================================================
nested_image_folder = os.path.join(extract_dir, "synthetic_recipe_images")

if os.path.exists(nested_image_folder):
    raw_files = os.listdir(nested_image_folder)
    valid_images = [f for f in raw_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if valid_images:
        # Get absolute, Windows-normalized path
        first_image_path = os.path.normpath(os.path.abspath(os.path.join(nested_image_folder, valid_images[0])))
        
        # 1. Use a context manager to load the image and immediately release the file lock
        with Image.open(first_image_path) as img:
            img.verify()  # Verifies the image is not broken
        
        # 2. FORCE Windows to open the unlocked file natively
        os.startfile(first_image_path)
        
        print(f"Successfully opened: {valid_images[0]}")
    else:
        print("⚠️ No valid image files (.png, .jpg) found inside the subfolder.")
else:
    print(f"⚠️ Could not find the subfolder path: {nested_image_folder}")