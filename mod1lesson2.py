# main.py
import json
import os
from PIL import Image
from pydantic import BaseModel, Field
import base64
import mimetypes

# Import config details and variables from your asset builder
from config import gemini_client
from downloader import recipes_json, extract_dir, setup_assets, user_reviews_json

# 1. Run the asset setup function and fetch the image file strings
image_files = setup_assets()

# 2. Open and load recipe JSON file data
with open(recipes_json, 'r', encoding='utf-8') as file:
    recipe_data = json.load(file)  

print("\n Key-Value Pairs of the First Recipe:")
if isinstance(recipe_data, list) and len(recipe_data) > 0:
    for key, value in recipe_data[0].items():
        print(f"{key}: {value}")
else:
    print("Recipe JSON data is empty or structurally invalid.")


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


def multimodal_llm_model(system_msg,user_msg,image_path):
    #Determine the image mime-type (e.g., image/png or image/jpeg)
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"  # Fallback

    with open(image_path,"rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')


    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": [
            {
                "type": "text",
                "text": user_msg
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            }
        ]}
    ]

    response = gemini_client.chat.completions.create(
    model='gemini-2.5-flash',
    messages=messages
    )

    output = response.choices[0].message.content
    return output

def image_caption_prompt_template(food_name):
    system_prompt = f"""You are an expert culinary AI assistant specialized in objective food analysis. 
        Your task is to analyze food images and describe them with high accuracy and precision. 
        Focus strictly on what is visually verifiable in the image: visible ingredients, colors, textures, plating style, and cooking methods.
        Do not speculate on taste, temperature, recipe names, or any details that cannot be directly seen."""
    
    user_prompt = f"""Analyze the provided food image of {food_name} and generate a structured caption containing:
        1. **Culinary Presentation**: Describe the plating style, serving dish, composition, and overall visual aesthetic.
        2. **Visible Ingredients**: List the ingredients and garnishes that are clearly visible in the dish.
        3. **Cooking Style & Texture**: Describe the visible textures (e.g., crispy, charred, creamy) and apparent preparation method (e.g., grilled, roasted, raw)."""
    
    return system_prompt,user_prompt


#test,
system_msg,user_msg = image_caption_prompt_template(recipe_data[0]["name"])
response = multimodal_llm_model(system_msg,user_msg,first_image_path)
print(response)
recipe_data[0]["image_description"] = response

#caption all images
for i in range(len(recipe_data)):
    image_path = os.path.normpath(os.path.abspath(os.path.join(nested_image_folder, valid_images[i])))
    system_msg,user_msg = image_caption_prompt_template(recipe_data[i]["name"])
    response = multimodal_llm_model(system_msg,user_msg,image_path)
    print(response)
    recipe_data[i]["image_description"] = response #create new caption field and add the response every time
print("All Done")

#write to the file
filename = 'augmented_food_recipe.json'
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(recipe_data, f,indent=4)


#USER REVIEW DATA
with open(user_reviews_json, 'r', encoding='utf-8') as file:
    user_review_data = json.load(file)  


    
