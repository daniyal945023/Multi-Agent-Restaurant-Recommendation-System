# downloader.py
import os
import zipfile
import urllib.request

recipes_json = "recipes.json"
user_reviews_json = "synthetic_user_reviews.json"
recipe_images_zip = "recipe_images.zip"
extract_dir = "recipe_images_extracted"

def ensure_assets_downloaded():
    # 1. Download JSON data only if missing
    if not os.path.exists(recipes_json):
        print("📥 Downloading Recipes JSON...")
        urllib.request.urlretrieve("https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/hpTjb6liKBLVHQK0UgMi5A/Recipes.json", recipes_json)
        
    if not os.path.exists(user_reviews_json):
        print("📥 Downloading User Reviews JSON...")
        urllib.request.urlretrieve("https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/fQUs9wQ6aB6ts6fmkD2V2w/Synthetic-User-Reviews.json", user_reviews_json)

    # 2. Download and unzip images only if the folder doesn't exist
    url = "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/5_Rr6ohviItzucyWk6nkrw/synthetic-recipe-images.zip"
    
    if not os.path.exists(extract_dir):
        print("--- Starting Safe Download ---")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as response:
                with open(recipe_images_zip, 'wb') as out_file:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        print(".", end="", flush=True)

            print("\n✅ Download finished completely!")
            print("--- Unzipping Archive ---")
            with zipfile.ZipFile(recipe_images_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print(f"✅ Folder '{extract_dir}' successfully created!")
            
            # Clean up the zip file to save space
            os.remove(recipe_images_zip)

        except Exception as e:
            print(f"\n❌ Execution failed: {e}")
            return []
            
    # 3. Read filenames directly from the directory instead of global variables
    all_files = os.listdir(extract_dir)
    return [f for f in all_files if not f.endswith("/")]
