from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
import json
import os
import shutil
import io
import unittest
from unittest.mock import patch
from config import gemini_client

# IMPORTANT: SOME PART IS REDONE FROM MODULE 1 LESSON 1

FILEPATH = 'structured_restaurant_data.json'
BACKUP_PATH = 'structured_restaurant_data.json.bak'
EXAMPLE_RESTAURANT_PARAGRAPH = 'Down in **Santa Monica**, **Mar de Cortez** serves as a **sun-drenched**, **casual taqueria** specializing in **Baja-style seafood**. With a **4.2/5** rating, it captures the salt-air energy of the coast through its signature beer-battered snapper tacos and zesty octopus ceviche, making it a premier spot for open-air dining near the pier. Price range: '
EXAMPLE_OUTPUT = """{
    "name": "Mar de Cortez",
    "location": "Santa Monica",
    "type": "casual taqueria",
    "food_style": "Baja-style seafood",
    "rating": 4.2,
    "price_range": 1,
    "signatures": [
        "beer-battered snapper tacos",
        "zesty octopus ceviche"
    ],
    "vibe": "salt-air energy",
    "environment": "a premier sun-drenched spot for open-air dining near the pier.",
    "shortcomings": []
}"""

class Restaurant(BaseModel):
    name: str
    location: str
    type: str
    food_style: str
    rating: Optional[float] = None
    price_range: Optional[int] = None
    signatures: List[str] = Field(default_factory=list)
    vibe: Optional[str] = None
    environment: str
    shortcomings: List[str] = Field(default_factory=list)


## Exercise 1: Integrate the LLM model from Lesson 1

def restaurant_data_structure_prompt_generation(restaurant_paragraph: str):
    base_system_prompt = f"""You are a precise data extraction engine. Your sole task is to transform unstructured paragraphs into a valid JSON object matching the exact structure and keys demonstrated in the user's provided example.

CRITICAL OPERATIONAL RULES:
1. OUTPUT FORMAT: Respond ONLY with a single, valid JSON object. Do not wrap the JSON inside markdown code blocks (e.g., do not use ```json ... ```). Do not include any introductory text, explanatory notes, or trailing comments.
2. SCHEMA COMPLIANCE: Your JSON output must match the exact data types, key names, and array structures shown in the user's template example.
3. DATA INTEGRITY: Extract information faithfully from the source text. Do not invent, extrapolate, or assume facts not explicitly stated in the paragraph.
4. MISSING DATA: If a specific field/key cannot be found in the unstructured text, set its value exactly to null (or an empty array `[]` for lists). Do not omit the key from the JSON structure.
"""
    base_user_prompt = f"""
    Task:
    Extract structured data from the provided "Restaurant description" and format it as a valid JSON object. 
    You must strictly follow the schema, key names, and data types shown in the "Example" below. 
    Do not add any conversational text, markdown formatting, or code blocks. Output the raw JSON string only.

    Restaurant description:
    {restaurant_paragraph}

    Example:
    Input Restaurant Description: {EXAMPLE_RESTAURANT_PARAGRAPH}
    Output:
    {EXAMPLE_OUTPUT}
    """

    return base_system_prompt, base_user_prompt


def llm_model(system_msg, user_msg, params=None):
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]

    response = gemini_client.chat.completions.create(
        model='gemini-2.5-flash',
        messages=messages
    )

    output = response.choices[0].message.content
    return output


def JSON_auto_repair_prompts(candidate_json_output, error_message):
    auto_repair_system_message = f"""You are a precise data correction engine specializing in Pydantic validation repairs. Your sole task is to take an invalid JSON payload that failed code validation, analyze the error feedback, and output a completely fixed, structural JSON object.

CRITICAL OPERATIONAL RULES:
1. OUTPUT FORMAT: Respond ONLY with a single, valid JSON object. Do not wrap the JSON inside markdown code blocks (e.g., do not use ```json ... ```). Do not include any introductory text, explanatory notes, or trailing comments.
2. SCHEMA ADHERENCE: You must alter the values, structural nesting, or missing keys strictly to satisfy the validation error rules provided.
3. PRESERVE INFORMATION: Retain all valid data points from the original wrong output. Only mutate fields that are explicitly causing the validation crash."""

    auto_repair_prompt = f""" Task:
    Analyze the provided "Invalid JSON Output" along with its corresponding validation failure details. Clean, reformat, and repair the payload so that it cleanly validates against the required Pydantic schema structure.

    Invalid JSON Output to Fix:
    {candidate_json_output}

    Pydantic Validation Error Details:
    {error_message}
    
    Output the corrected raw JSON string only.
    """

    return auto_repair_system_message, auto_repair_prompt


def new_data_entry_process(paragraph, itemId):
    system_msg, user_msg = restaurant_data_structure_prompt_generation(paragraph)
    json_response = llm_model(system_msg, user_msg)
    
    attempts = 0
    max_attempts = 3  # Prevent endless loops if the API behaves weirdly
    data = None       # Initialize data container

    while attempts < max_attempts:
        try:
            # Clean possible markdown wrapping blocks
            clean_json_string = json_response.replace("```json", "").replace("```", "").strip()
            # Validate and convert into a Restaurant model
            data = Restaurant.model_validate_json(clean_json_string)
            print(f"Success! Validated: {data.name}")
            break
        except ValidationError as e:
            attempts += 1
            print(f"Validation failed (Attempt {attempts}/{max_attempts}): {e.json()}")
            if attempts >= max_attempts:
                print(f"Skipping restaurant ID {itemId} after {max_attempts} failed repair attempts.")
                break
            
            # Use self-repair prompt to let the LLM fix the validation errors
            correction_system_prompt, correction_user_prompt = JSON_auto_repair_prompts(json_response, e.json())
            json_response = llm_model(correction_system_prompt, correction_user_prompt)

    # Return python dictionary if we successfully parsed and validated the object
    if data is not None:
        restaurant_dict = data.model_dump()
        restaurant_dict['itemId'] = itemId
        return restaurant_dict
    return None


def save_data(file_path, data, backup_path=None):
    """Safely saves the data list into a JSON file with an optional backup file creation."""
    if backup_path and os.path.exists(file_path):
        shutil.copy2(file_path, backup_path)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        restaurants = json.load(f)
    return restaurants


def show_restaurant_card(res, index):
    print(
        f"""
        === Restaurant Info [Index: {index}] ===
        Name: {res.get("name", "N/A")}
        Location: {res.get("location", "N/A")}
        Food Style: {res.get("food_style", "N/A")}
        Type: {res.get("type", "N/A")}
        Rating: {res.get("rating", "N/A")}
        Price Range: {res.get("price_range", "N/A")}
        Signatures: {res.get("signatures", [])}
        Vibe: {res.get("vibe", "N/A")}
        Environment: {res.get("environment", "N/A")}
        Shortcomings: {res.get("shortcomings", [])}
        """
    )


def manage_restaurants(file_path, backup_path):
    while True:
        data = load_data(file_path)  # get the list
        print(f"\n🏨 RESTAURANT DATABASE | Records: {len(data)}")
        print("1. Browse All (Names)")
        print("2. View Detailed Record")
        print("3. Add New Restaurant")
        print("4. Edit Restaurant Info")
        print("5. Delete Restaurant")
        print("6. Exit")
        
        choice = input("\nAction: ")

        if choice == '1':
            print("\n--- Current Listings ---")
            for i in range(len(data)):
                name = data[i].get("name")
                if name:
                    print(f"[{i}] {name}")
                else:
                    print(f"[{i}] N/A")
        
        elif choice == '2':
            record_index = input(">Enter your desired index: ")
            try:
                record_index = int(record_index)
                if 0 <= record_index < len(data):
                    show_restaurant_card(data[record_index], record_index)
                else:
                    print("invalid index.")
            except ValueError:
                print("Please enter a valid number.")

        elif choice in ['3', '4', '5']:
            # Strict Security Warning
            print("\n❗ SECURITY WARNING: You are entering write-mode.")
            print("Changes will be saved to the database immediately.")
            confirm = input("Are you sure? (type 'yes' to proceed): ").lower()
            if confirm != 'yes':
                print("Operation cancelled.")
                continue

            if choice == '3': # ADD NEW DATA
                itemId = 1000000 + len(data) + 1  # the item id for the new data
                
                user_description = input("Enter restaurant description: ")
                new_restaurant = new_data_entry_process(user_description, itemId)
                
                if new_restaurant:
                    data.append(new_restaurant)
                    save_data(file_path, data, backup_path)
                    print(f"✅ Successfully added '{new_restaurant['name']}' to database.")
                else:
                    print("❌ Could not process and validate the restaurant.")

            elif choice == '4': # EDIT DATA
                record_index = input(">Enter the index of the restaurant to edit: ")
                try:
                    record_index = int(record_index)
                    if 0 <= record_index < len(data):
                        restaurant = data[record_index]
                        print("Leave blank to keep current value.")
                        for key in restaurant.keys():
                            if key == 'itemId':
                                continue  # Don't manually change IDs
                            
                            current_value = restaurant[key]
                            if isinstance(current_value, list):
                                current_value_str = ", ".join(current_value)
                            else:
                                current_value_str = str(current_value)
                            
                            new_value = input(f"{key} [{current_value_str}]: ")
                            if new_value.strip() != "":
                                # Maintain structural type integrity during manual edit updates
                                if isinstance(restaurant[key], list):
                                    restaurant[key] = [item.strip() for item in new_value.split(",")]
                                elif isinstance(restaurant[key], int):
                                    restaurant[key] = int(new_value)
                                elif isinstance(restaurant[key], float):
                                    restaurant[key] = float(new_value)
                                else:
                                    restaurant[key] = new_value
                                    
                        save_data(file_path, data, backup_path)
                        print("✅ Record updated.")
                    else:
                        print("invalid index.")
                except ValueError:
                    print("Please enter a valid number.")

            elif choice == '5': # DELETE DATA
                record_index = input(">Enter the index of the restaurant to delete: ")
                try:
                    record_index = int(record_index)
                    if 0 <= record_index < len(data):
                        removed = data.pop(record_index)
                        save_data(file_path, data, backup_path)
                        print(f"✅ Deleted '{removed['name']}'.")
                    else:
                        print("invalid index.")
                except ValueError:
                    print("Please enter a valid number.")

        elif choice == '6': # EXIT
            break
        else:
            print("Invalid input.")

# RUN THE UI
if __name__ == "__main__":
    manage_restaurants(FILEPATH, BACKUP_PATH)