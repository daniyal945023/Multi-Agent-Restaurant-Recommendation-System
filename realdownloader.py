import json
import os
import zipfile
import urllib.request
from PIL import Image

recipes_json = "recipes.json"
user_reviews_json = "synthetic_user_reviews.json"


urllib.request.urlretrieve("https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/hpTjb6liKBLVHQK0UgMi5A/Recipes.json", recipes_json)

urllib.request.urlretrieve("https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/fQUs9wQ6aB6ts6fmkD2V2w/Synthetic-User-Reviews.json", user_reviews_json)


url = "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/5_Rr6ohviItzucyWk6nkrw/synthetic-recipe-images.zip"  # Put your actual zip URL here
recipe_images_zip = "recipe_images.zip"
extract_dir = "recipe_images_extracted"

print("--- Starting Safe Download ---")

# 1. Use clean browser headers to stop the server from blocking you
req = urllib.request.Request(
    url, 
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
)

try:
    # 2. Download and write file piece-by-piece to prevent memory freezes
    with urllib.request.urlopen(req) as response:
        with open(recipe_images_zip, 'wb') as out_file:
            while True:
                chunk = response.read(1024 * 256)  # Read in 256KB pieces
                if not chunk:
                    break
                out_file.write(chunk)
                print(".", end="", flush=True)  # Print progress dots

    print("\n✅ Download finished completely and saved to disk!")

    # 3. Check if file is physically present and valid
    if os.path.exists(recipe_images_zip) and os.path.getsize(recipe_images_zip) > 0:
        print("--- Unzipping Archive ---")
        
        # 4. Open and extract everything to your folder path
        with zipfile.ZipFile(recipe_images_zip, 'r') as zip_ref:
            extracted_recipe_images = zip_ref.namelist()
            zip_ref.extractall(extract_dir)
            
        print(f"✅ Folder '{extract_dir}' successfully created!")

        #5.isolate images
    else:
        print("❌ File was not successfully written to your local drive.")

except Exception as e:
    print(f"\n❌ Execution failed: {e}")
