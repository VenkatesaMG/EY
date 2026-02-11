# groq_compare.py
import json
import os
from Validation.groq_client import generate_text

def compare_row_with_npi_groq(row: dict, npi_info: dict) -> dict:
    """
    Use Groq (Llama 3) to compare a CSV provider row with NPI info.

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

    # JSON schema so Groq returns proper structured JSON.
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

SCHEMA:
{json.dumps(result_schema, indent=2)}
"""

    try:
        response_text = generate_text(prompt, json_mode=True, model="llama-3.3-70b-versatile")
        return json.loads(response_text)
    except Exception as e:
        print(f"Groq Parsing Error: {e}")
        # Fallback empty structure
        return {
            "overall_match": False,
            "confidence": 0,
            "fields": {},
            "issues": ["parsing_error"],
            "explanation": str(e)
        }
