from config import gemini_client
import numpy as np
import matplotlib.pyplot as plt
import json
import urllib.request
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

#GOAL: CONVERT PARAGRAPH DATA INTO STRUCTURED JSON DATA USING LLM AND PYDANTIC VALIDATION

#fetch the data file
output_file = "californa_culinary_map.txt"

urllib.request.urlretrieve("https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/1r_mM6ZPYNxcFv65QkzubA/California-Culinary-Map.txt", output_file)

##read file
with open(output_file, 'r') as file:
    restaurant_data = file.read()

restaurant_list = restaurant_data.split("\n\n") #list of paragraphs(each para has info of each restaurant)
restaurant_list = restaurant_list[1:] #remove heading of dataset

#create llm model
def llm_model(system_msg,user_msg):
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


EXAMPLE_RESTAURANT_PARAGRAPH = restaurant_list[1] #use the second restaurant paragraph as the example
EXAMPLE_OUTPUT = """
    {{
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
    }}
"""

def generate_prompt(restaurant_paragraph: str):
    base_system_prompt = f"""You are a precise data extraction engine. Your sole task is to transform unstructured paragraphs into a valid JSON object matching the exact structure and keys demonstrated in the user's provided example.

CRITICAL OPERATIONAL RULES:
1. OUTPUT FORMAT: Respond ONLY with a single, valid JSON object. Do not wrap the JSON inside markdown code blocks (e.g., do not use ```json ... ```). Do not include any introductory text, explanatory notes, or trailing comments.
2. SCHEMA COMPLIANCE: Your JSON output must match the exact data types, key names, and array structures shown in the user's template example.
3. DATA INTEGRITY: Extract information faithfully from the source text. Do not invent, extrapolate, or assume facts not explicitly stated in the paragraph.
4. MISSING DATA: If a specific field/key cannot be found in the unstructured text, set its value exactly to null (or an empty array `[]` for lists). Do not omit the key from the JSON structure.
"""
    base_user_prompt = base_user_prompt = f"""
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

    return base_system_prompt,base_user_prompt



#define output schema(to validate llm response in case it gives incorrect msg)
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




#another llm system to correct the validation errors by previous llm system
def JSON_auto_repair_prompt(candidate_json_output,error_message):
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

    return auto_repair_system_message,auto_repair_prompt


structured_restaurant_list = [] #save structured json data in this list
for i,restaurant_paragraph in enumerate(restaurant_list):
    system_prompt,user_prompt = generate_prompt(restaurant_paragraph)
    candidate_json_response = llm_model(system_prompt,user_prompt)

    attempts = 0
    max_attempts = 3  # Prevent endless loops if the API behaves weirdly

    while attempts < max_attempts:
        #test whether the llm outputs according to schema or not
        try:
            clean_json_string = candidate_json_response.replace("```json", "").replace("```", "").strip() #cleaning,incase llm returns in markdown block format
            data = Restaurant.model_validate_json(clean_json_string) #returns structed pydantic object
            print(f"Success! Validated: {data.name}")
            #if validated,append to structuredlist
            structured_restaurant_list.append(data)
            break
        except ValidationError as e:
            attempts += 1
            print(f"Validation failed: {e.json()}")
            if attempts >= max_attempts:
                print(f"Skipping restaurant {i} after {max_attempts} failed repair attempts.")
                break
            correction_system_prompt,correction_user_prompt = JSON_auto_repair_prompt(candidate_json_response,e.json())
            candidate_json_response = llm_model(correction_system_prompt,correction_user_prompt)
    #manual progress bar
    if (i+1)%20 == 0:
        print(f'{i+1} out of {len(restaurant_list)} is done')

# A final message to notify the completion
print('ALL DONE!!')


print(structured_restaurant_list[49])

#convert json to python dictionary using json.loads
structured_restaurant_lists_json = [json.loads(response) for response in structured_restaurant_list]

#For each item in the restaurant list, assign it with an itemId to be consistent with the one in the user review data:
for i, response in enumerate(structured_restaurant_lists_json):
    response['itemId'] = 1000001 + i
    structured_restaurant_lists_json[i] = response
    
filename = 'structured_restaurant_data.json'
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(structured_restaurant_lists_json, f, indent=4)
    #dump the data into the file
















