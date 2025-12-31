# gemini_compare.py
import json
import os
from google import genai  # official Google Gen AI SDK
from google.genai import types
from dotenv import load_dotenv

# Client picks up GEMINI_API_KEY / GOOGLE_API_KEY from env by default. [web:71]
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def compare_row_with_npi_gemini(row: dict, npi_info: dict) -> dict:
    """
    Use Gemini to compare a CSV provider row with NPI info.

    Returns a JSON dict like:
    {
      "overall_match": true/false,
      "confidence": 0-100,
      "fields": {
         "name": {"match": true, "reason": "..."},
         "address": {"match": true, "reason": "..."},
         "phone": {"match": false, "reason": "..."},
         "specialty": {"match": true, "reason": "..."}
      },
      "issues": ["phone_mismatch", "city_mismatch"],
      "explanation": "Natural language explanation..."
    }
    """

    # Subset NPI info to only what the model needs (avoid huge raw blob)
    npi_payload = {
        "npi": npi_info.get("npi"),
        "first_name": npi_info.get("first_name"),
        "last_name": npi_info.get("last_name"),
        "primary_practice_address": npi_info.get("primary_practice_address"),
        "primary_taxonomy": npi_info.get("primary_taxonomy"),
    }

    # JSON schema so Gemini returns proper structured JSON. [web:68][web:71]
    result_schema = {
        "type": "object",
        "properties": {
            "overall_match": {"type": "boolean"},
            "confidence": {"type": "number"},
            "fields": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "object",
                        "properties": {
                            "match": {"type": "boolean"},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["match", "confidence", "reason"],
                    },
                    "address": {
                        "type": "object",
                        "properties": {
                            "match": {"type": "boolean"},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["match", "confidence", "reason"],
                    },
                    "phone": {
                        "type": "object",
                        "properties": {
                            "match": {"type": "boolean"},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["match", "confidence", "reason"],
                    },
                    "specialty": {
                        "type": "object",
                        "properties": {
                            "match": {"type": "boolean"},
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["match", "confidence", "reason"],
                    },
                },
                "required": ["name", "address", "phone", "specialty"],
            },
            "issues": {
                "type": "array",
                "items": {"type": "string"},
            },
            "explanation": {"type": "string"},
        },
        "required": ["overall_match", "confidence", "fields", "issues", "explanation"],
    }

    prompt = f"""
You are validating a health plan's provider directory row against official NPI data.

CSV ROW (directory record):
{json.dumps(row, indent=2)}

NPI RECORD (official registry subset):
{json.dumps(npi_payload, indent=2)}

Tasks:
1. Decide if this looks like the same provider and location.
2. For each field (name, address, phone, specialty), say whether it matches, provide a confidence score (0.0-1.0), and why.
3. Identify issues, e.g. "phone_mismatch", "address_mismatch", "name_mismatch", "specialty_mismatch".
4. Give an overall confidence from 0 to 100.
5. Return ONLY JSON matching the given schema. Do not include any extra keys.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",  # fast, cheap model is fine here [web:65][web:70]
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": result_schema,
            # You can also set temperature low for determinism:
            # "generation_config": {"temperature": 0.1},
        },
    )

    # SDK can parse JSON directly when schema is provided. [web:68][web:71]
    try:
        return response.parsed  # already a Python dict
    except AttributeError:
        # Fallback: manually parse text if needed
        return json.loads(response.text)
