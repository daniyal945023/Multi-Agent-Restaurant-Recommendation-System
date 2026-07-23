from typing import List, Optional

import openai
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from config import gemini_client


EXAMPLE_RESTAURANT_PARAGRAPH = (
    "Down in **Santa Monica**, **Mar de Cortez** serves as a **sun-drenched**, "
    "**casual taqueria** specializing in **Baja-style seafood**. With a **4.2/5** "
    "rating, it captures the salt-air energy of the coast through its signature "
    "beer-battered snapper tacos and zesty octopus ceviche, making it a premier "
    "spot for open-air dining near the pier. Price range: 1"
)

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


def restaurant_data_structure_prompt(restaurant_paragraph: str):
    system_prompt = """You are a precise data extraction engine. Your sole task is to transform unstructured paragraphs into a valid JSON object matching the exact structure and keys demonstrated in the user's provided example.

CRITICAL OPERATIONAL RULES:
1. OUTPUT FORMAT: Respond ONLY with a single, valid JSON object. Do not wrap the JSON inside markdown code blocks (e.g., do not use ```json ... ```). Do not include any introductory text, explanatory notes, or trailing comments.
2. SCHEMA COMPLIANCE: Your JSON output must match the exact data types, key names, and array structures shown in the user's template example.
3. DATA INTEGRITY: Extract information faithfully from the source text. Do not invent, extrapolate, or assume facts not explicitly stated in the paragraph.
4. MISSING DATA: If a specific field/key cannot be found in the unstructured text, set its value exactly to null (or an empty array `[]` for lists). Do not omit the key from the JSON structure.
"""
    user_prompt = f"""
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

    return system_prompt, user_prompt


def json_auto_repair_prompt(candidate_json_output, error_message):
    system_prompt = """You are a precise data correction engine specializing in Pydantic validation repairs. Your sole task is to take an invalid JSON payload that failed code validation, analyze the error feedback, and output a completely fixed, structural JSON object.

CRITICAL OPERATIONAL RULES:
1. OUTPUT FORMAT: Respond ONLY with a single, valid JSON object. Do not wrap the JSON inside markdown code blocks (e.g., do not use ```json ... ```). Do not include any introductory text, explanatory notes, or trailing comments.
2. SCHEMA ADHERENCE: You must alter the values, structural nesting, or missing keys strictly to satisfy the validation error rules provided.
3. PRESERVE INFORMATION: Retain all valid data points from the original wrong output. Only mutate fields that are explicitly causing the validation crash."""

    user_prompt = f""" Task:
    Analyze the provided "Invalid JSON Output" along with its corresponding validation failure details. Clean, reformat, and repair the payload so that it cleanly validates against the required Pydantic schema structure.

    Invalid JSON Output to Fix:
    {candidate_json_output}

    Pydantic Validation Error Details:
    {error_message}

    Output the corrected raw JSON string only.
    """

    return system_prompt, user_prompt


@retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(multiplier=2, min=4, max=30),
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)),
)
def llm_model(system_msg, user_msg):
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    response = gemini_client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=messages,
    )

    return response.choices[0].message.content


def clean_json_response(json_response: str) -> str:
    return json_response.replace("```json", "").replace("```", "").strip() #sometimes llm may give response in markdown,this fixes it
