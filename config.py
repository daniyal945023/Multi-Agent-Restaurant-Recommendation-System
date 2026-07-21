import os
from openai import OpenAI
from dotenv import load_dotenv

# Automatically look for and load variables from your .env file
load_dotenv()


# Build the centralized client instance
gemini_client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
