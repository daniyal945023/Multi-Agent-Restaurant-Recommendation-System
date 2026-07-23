import json
import time
import urllib.request
from pydantic import ValidationError

from restaurant_llm import (
    Restaurant,
    clean_json_response,
    json_auto_repair_prompt,
    llm_model,
    restaurant_data_structure_prompt,
)

#GOAL: CONVERT PARAGRAPH DATA INTO STRUCTURED JSON DATA USING LLM AND PYDANTIC VALIDATION

DATA_URL = "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/1r_mM6ZPYNxcFv65QkzubA/California-Culinary-Map.txt"
OUTPUT_FILE = "california_culinary_map.txt"
JSON_OUTPUT_FILE = "structured_restaurant_data.json"
REQUEST_DELAY_SECONDS = 1
MAX_REPAIR_ATTEMPTS = 3


def load_restaurant_paragraphs(output_file=OUTPUT_FILE):
    urllib.request.urlretrieve(DATA_URL, output_file)

    with open(output_file, "r", encoding="utf-8") as file:
        restaurant_data = file.read()

    restaurant_list = restaurant_data.split("\n\n") #separate the data by paragraph and convert to list
    return restaurant_list[1:] #return the list without the dataset heading(first para)

#turns paragraph into structured data with llm and pydantic validations and returns it
def structure_and_validate_restaurant(restaurant_paragraph, index, max_attempts=MAX_REPAIR_ATTEMPTS):
    system_prompt, user_prompt = restaurant_data_structure_prompt(restaurant_paragraph)
    candidate_json_response = llm_model(system_prompt, user_prompt)

    attempts = 0
    while attempts < max_attempts:
        try:  #model_validate_json returns pydantic object
            data = Restaurant.model_validate_json(clean_json_response(candidate_json_response))
            print(f"Success! Validated: {data.name}")
            return data
        except ValidationError as e:
            attempts += 1
            print(f"Validation failed: {e.json()}")
            if attempts >= max_attempts:
                print(f"Skipping restaurant {index} after {max_attempts} failed repair attempts.")
                return None
            correction_system_prompt, correction_user_prompt = json_auto_repair_prompt(
                candidate_json_response,
                e.json(),
            )
            candidate_json_response = llm_model(correction_system_prompt, correction_user_prompt)


def build_structured_restaurant_data(request_delay_seconds=REQUEST_DELAY_SECONDS):
    restaurant_list = load_restaurant_paragraphs()
    structured_restaurant_list = []

    for i, restaurant_paragraph in enumerate(restaurant_list):
        data = structure_and_validate_restaurant(restaurant_paragraph, i) #get llm response and validate each restaurant
        if data is not None:
            structured_restaurant_list.append(data) #append pydantic object to list

        if request_delay_seconds:
            time.sleep(request_delay_seconds)

        if (i + 1) % 20 == 0:  #track progress
            print(f"{i + 1} out of {len(restaurant_list)} is done")

    structured_restaurant_lists_json = [
        response.model_dump() for response in structured_restaurant_list
    ] #convert each pydantic object in list to python dicts

    for i, response in enumerate(structured_restaurant_lists_json):
        response["itemId"] = 1000001 + i   #set unique id

    with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(structured_restaurant_lists_json, f, indent=4) #convert the list of dicts into a list of json data and save to json output file

    print("ALL DONE!!")
    return structured_restaurant_lists_json  #return the list of dicts


if __name__ == "__main__":
    build_structured_restaurant_data()
















