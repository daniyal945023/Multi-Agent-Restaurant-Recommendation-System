from pydantic import ValidationError
import json
import os
import shutil
import time

from restaurant_llm import (
    Restaurant,
    clean_json_response,
    json_auto_repair_prompt,
    llm_model,
    restaurant_data_structure_prompt,
)

FILEPATH = 'structured_restaurant_data.json'
BACKUP_PATH = 'structured_restaurant_data.json.bak'
REQUEST_DELAY_SECONDS = 1


def new_data_entry_process(paragraph, itemId):
    system_msg, user_msg = restaurant_data_structure_prompt(paragraph)
    json_response = llm_model(system_msg, user_msg)
    
    attempts = 0
    max_attempts = 3  # Prevent endless loops if the API behaves weirdly
    data = None       # Initialize data container

    while attempts < max_attempts:
        try:
            # Clean possible markdown wrapping blocks
            clean_json_string = clean_json_response(json_response)
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
            correction_system_prompt, correction_user_prompt = json_auto_repair_prompt(json_response, e.json())
            if REQUEST_DELAY_SECONDS:
                time.sleep(REQUEST_DELAY_SECONDS)
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
    if not os.path.exists(file_path):
        print(f"Could not find {file_path}. Run mod1lesson1.py first to create it.")
        return

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
                if 0 <= record_index < len(data): #show only IF record index lies b/w 0 and len-1
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
                continue #re-ask for choice, if answer is not yes

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
                                current_value_str = ", ".join(current_value) #if the value of key is a list,convert it to comma separated string
                            else:
                                current_value_str = str(current_value) #else just convert to string
                            
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
