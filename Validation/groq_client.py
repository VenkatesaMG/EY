import os
from groq import Groq
import json
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def generate_text(prompt: str, json_mode: bool = False, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Generates text using Groq API.
    """
    client = Groq(api_key=GROQ_API_KEY)
    
    try:
        kwargs = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 16382,
            "top_p": 1,
            "stream": False,
            "stop": None
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        completion = client.chat.completions.create(**kwargs)
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"Groq API Request Failed: {e}")
        raise
