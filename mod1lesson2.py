# main.py
import json
import os
import openai
from PIL import Image
from pydantic import BaseModel, Field
import base64
import mimetypes
import ast
import requests
from tenacity import retry, stop_after_attempt, wait_exponential,retry_if_exception_type

# Import config details and variables from your asset builder
from config import gemini_client
from downloader import recipes_json, extract_dir, setup_assets, user_reviews_json

# Retry if we hit an OpenAI API connection/rate limit exception
@retry(
    stop=stop_after_attempt(5), 
    wait=wait_exponential(multiplier=2, min=4, max=16),
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError))
)
def multimodal_llm_model(system_msg, user_msg, image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": [
            {"type": "text", "text": user_msg},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
        ]}
    ]

    response = gemini_client.chat.completions.create(
        model='gemini-2.5-flash',
        messages=messages
    )
    return response.choices[0].message.content


def recipe_image_caption_prompt_template(food_name):
    system_prompt = """You are an expert culinary AI assistant specialized in objective food analysis. 
Your task is to analyze food images and describe them with high accuracy and precision. 
Focus strictly on what is visually verifiable in the image: visible ingredients, colors, textures, plating style, and cooking methods.
Do not speculate on taste, temperature, recipe names, or any details that cannot be directly seen."""
    
    user_prompt = f"""Analyze the provided food image of {food_name} and generate a structured caption containing:
1. **Culinary Presentation**: Describe the plating style, serving dish, composition, and overall visual aesthetic.
2. **Visible Ingredients**: List the ingredients and garnishes that are clearly visible in the dish.
3. **Cooking Style & Texture**: Describe the visible textures (e.g., crispy, charred, creamy) and apparent preparation method (e.g., grilled, roasted, raw)."""
    
    return system_prompt, user_prompt


def review_image_caption_prompt_template(reviews):
    system_prompt = """You are an expert culinary AI assistant with a deep understanding of food quality, presentation, and dining experiences. Your task is to analyze a food image alongside its corresponding customer review. Describe the visual details of the image concisely while aligning your focus with the specific observations, details, and sentiment expressed in the user's review."""
    
    user_prompt = f"""Here is the customer's review:
---
"{reviews}"
---

Please analyze the provided food image. Generate a concise visual description of the dish that:
1. Focuses on the specific details mentioned in the review (such as portions, presentation, specific ingredients, or cooking quality).
2. Corroborates and aligns with the customer's feedback and sentiment based strictly on what is visually verifiable in the photo."""
    
    return system_prompt, user_prompt

@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=1, max=10))
def get_data_with_retry(url):
    response = requests.get(url, timeout=5)
    response.raise_for_status() # Must raise error for retry to trigger
    return response

#MAIN FUNCTION for execution
if __name__ == "__main__":
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
        
    else:
        print(f"⚠️ Could not find the subfolder path: {nested_image_folder}")

    

    # Caption all images
    for i in range(len(recipe_data)):
        image_path = os.path.normpath(os.path.abspath(os.path.join(nested_image_folder, valid_images[i])))
        system_msg, user_msg = recipe_image_caption_prompt_template(recipe_data[i]["name"])
        response = multimodal_llm_model(system_msg, user_msg, image_path)
        print(response)
        recipe_data[i]["image_description"] = response 
    print("All Done")

    # Write to the file
    filename = 'augmented_food_recipe.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(recipe_data, f, indent=4, ensure_ascii=False)

    # USER REVIEW DATA
    with open(user_reviews_json, 'r', encoding='utf-8') as file:
        user_review_data = json.load(file)  

    print("\n Key-Value Pairs of the First User Review:")
    if isinstance(user_review_data, list) and len(user_review_data) > 0:
        for key, value in user_review_data[0].items():
            print(f"{key}: {value}")
    else:
        print("User Review JSON data is empty or structurally invalid.")

    #workflow for i items in user_review_data
    for i in range(len(user_review_data)):
       img_url_list = ast.literal_eval(user_review_data[i]["images"]) #convert stuck list in string to a list
       review_image_captions = []
       if len(img_url_list) > 0:
            for img_url in img_url_list:
                  try:
                    img_data = get_data_with_retry(img_url)
                    print("Success")
                  except Exception as e:
                   print(f"All retries failed at url {img_url}:", e)
                   continue

                  image_placeholder_path = "review_image_placeholder.jpg"
                  with open(image_placeholder_path, 'wb') as file:
                     file.write(img_data.content) #write data in .jpg file
            
                  system_msg,user_msg = review_image_caption_prompt_template(user_review_data[i]["text"])
                  llm_response = multimodal_llm_model(system_msg,user_msg,"review_image_placeholder.jpg")
                  review_image_captions.append(llm_response)
            
       user_review_data[i]['image_captions'] = review_image_captions
    


    filename = 'augmented_user_review_data.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(user_review_data, f,indent=4, ensure_ascii=False)