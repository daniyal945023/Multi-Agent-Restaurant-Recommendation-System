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
import time
from tenacity import retry, stop_after_attempt, wait_exponential,retry_if_exception_type

# Import config details and variables from your asset builder
from config import gemini_client
from downloader import recipes_json, extract_dir, ensure_assets_downloaded, user_reviews_json

#OUR MAIN GOAL HERE IS TO GET CAPTIONS(TEXTUAL CONTEXT) FROM IMAGES IN RECIPES AND REVIEWS
REQUEST_DELAY_SECONDS = 1
RECIPE_OUTPUT_FILE = 'augmented_food_recipe.json'
REVIEW_OUTPUT_FILE = 'augmented_user_review_data.json'


def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_json_if_exists(filename):
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError:
        print(f"Could not resume from {filename}; rebuilding it.")
        return None


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
    ensure_assets_downloaded()

    # 2. Open and load recipe JSON file data
    recipe_data = load_json_if_exists(RECIPE_OUTPUT_FILE)
    if recipe_data is None:
        with open(recipes_json, 'r', encoding='utf-8') as file:
            recipe_data = json.load(file)  #json.load converts list of json objects in file into python list of dicts
    else:
        print(f"Resuming recipe captions from {RECIPE_OUTPUT_FILE}.")

    print("\n Key-Value Pairs of the First Recipe:")
    if isinstance(recipe_data, list) and len(recipe_data) > 0:
        for key, value in recipe_data[0].items():
            print(f"{key}: {value}")
    else:
        print("Recipe JSON data is empty or structurally invalid.")

    nested_image_folder = os.path.join(extract_dir, "synthetic_recipe_images")

    if os.path.exists(nested_image_folder):
        raw_files = os.listdir(nested_image_folder) #save all files of nested_image_folder in a list
        valid_images = sorted(f for f in raw_files if f.lower().endswith(('.png', '.jpg', '.jpeg')))
        #filter out only the image files
        
    else:
        raise FileNotFoundError(f"Could not find image folder: {nested_image_folder}")

    

    # use llm to generate caption for each image
    for i in range(len(recipe_data)):
        if recipe_data[i].get("image_description"):
            continue

        image_path = os.path.normpath(os.path.abspath(os.path.join(nested_image_folder, valid_images[i])))
        system_msg, user_msg = recipe_image_caption_prompt_template(recipe_data[i]["name"])
        try:
            response = multimodal_llm_model(system_msg, user_msg, image_path)
        except Exception as e:
            print(f"Stopping recipe captions at index {i} after retries failed: {e}")
            break
        recipe_data[i]["image_description"] = response  #save llm response in recipe data i.e the list of dicts with a new key
        save_json(RECIPE_OUTPUT_FILE, recipe_data)
        if REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS)
    print("All Done")
    save_json(RECIPE_OUTPUT_FILE, recipe_data) #save the modified recipe_data in a new file

    # USER REVIEW DATA
    user_review_data = load_json_if_exists(REVIEW_OUTPUT_FILE)
    if user_review_data is None:
        with open(user_reviews_json, 'r', encoding='utf-8') as file:
            user_review_data = json.load(file) #again convert the list of json into python list of dicts to work with it 
    else:
        print(f"Resuming review captions from {REVIEW_OUTPUT_FILE}.")

    print("\n Key-Value Pairs of the First User Review:")
    if isinstance(user_review_data, list) and len(user_review_data) > 0:
        for key, value in user_review_data[0].items():
            print(f"{key}: {value}")
    else:
        print("User Review JSON data is empty or structurally invalid.")

    #workflow for i items in user_review_data
    stop_review_processing = False
    for i in range(len(user_review_data)):
       if "image_captions" in user_review_data[i]:
            continue

       img_url_list = ast.literal_eval(user_review_data[i]["images"]) #convert stuck list in string to a list
       review_image_captions = []
       if len(img_url_list) > 0:
            for img_url in img_url_list:
                  try:
                    img_data = get_data_with_retry(img_url)
                    print("Success")
                  except Exception as e:
                   print(f"All retries failed at url {img_url}:", e)
                   continue  #skip the dict if image fetching from url failed

                  image_placeholder_path = "review_image_placeholder.jpg"
                  with open(image_placeholder_path, 'wb') as file:
                     file.write(img_data.content) #write data in .jpg file
            
                  system_msg,user_msg = review_image_caption_prompt_template(user_review_data[i]["text"])
                  try:
                    llm_response = multimodal_llm_model(system_msg,user_msg,"review_image_placeholder.jpg")
                  except Exception as e:
                   print(f"Stopping review captions at review index {i} after retries failed: {e}")
                   stop_review_processing = True
                   break
                  review_image_captions.append(llm_response)
                  if REQUEST_DELAY_SECONDS:
                    time.sleep(REQUEST_DELAY_SECONDS)
            
       if stop_review_processing:
            break

       user_review_data[i]['image_captions'] = review_image_captions
       save_json(REVIEW_OUTPUT_FILE, user_review_data)
    
    save_json(REVIEW_OUTPUT_FILE, user_review_data)
