import os
import atexit
import time
import json
from dotenv import load_dotenv
# import ollama  <-- Removed
# from Validation.groq_client import generate_text # Need to handle import path carefully or duplicate client
# Assuming the running context allows this import, as services.py does it.
from Validation.groq_client import generate_text

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

# Helper functions moved inside class or context manager usage
# For simplicity and thread-safety, we will create a fresh driver for each enrichment task.
# This adds overhead (2-3s setup) but GUARANTEES no session conflicts in threaded environment.

def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def search_web_with_driver(driver, query: str):
    urls = []
    try:
        print(f"DEBUG: Searching DuckDuckGo for '{query}'...")
        driver.get(f"https://html.duckduckgo.com/html/?q={query}")
        time.sleep(2)
        elements = driver.find_elements(By.CSS_SELECTOR, ".result")
        for el in elements[:3]: 
            try:
                link_el = el.find_element(By.CSS_SELECTOR, "a.result__a")
                urls.append(link_el.get_attribute("href"))
            except: continue
    except Exception as e:
        print(f"Search Error: {e}")
    return urls

def scrape_webpage_with_driver(driver, url: str):
    try:
        print(f"DEBUG: Scraping {url}...")
        driver.get(url)
        time.sleep(1)
        body = driver.find_element(By.TAG_NAME, "body").text
        clean_body = " ".join(body.split())
        return clean_body[:3000] 
    except Exception as e:
        print(f"Scrape Error: {e}")
        return ""

class EnrichmentManager:
    def __init__(self):
        # self.model = "qwen2.5:7b" # Replaced by Groq model default in client
        
        self.system_prompt = """
        You are a Healthcare Data Structuring Engine. 
        Your job is to read unstructured text from provider websites and map it to a strict JSON schema.

        ### EXTRACTION RULES:
        1. **Boolean Logic**: 
           - 'accepting_new_patients': Set to true ONLY if you see "Accepting new patients" or similar. Default to null if unsure.
           - 'telehealth': Set to true if "Telemedicine", "Virtual Visits", or "Video" are mentioned.
        2. **Arrays**:
           - 'specialties': Extract all medical specialties listed (e.g., ["Cardiology", "Internal Medicine"]).
           - 'languages': Extract languages spoken (e.g., ["English", "Spanish"]).
        3. **Confidence**:
           - 'overall_confidence': Rate from 0.0 to 1.0 based on how much data you found on the page.
        4. **Null Handling**:
           - If a field is not found in the text, return null (do not hallucinate).

        ### REQUIRED JSON OUTPUT FORMAT:
        {
            "display_name": "Full Name found on page",
            "npi": "10-digit NPI if found",
            "taxonomy_code": "Taxonomy code if found",
            "specialties": ["Specialty 1", "Specialty 2"],
            "phone": "Primary phone number",
            "email": "Email address",
            "website": "URL of the practice",
            "practice_name": "Name of the clinic/hospital",
            "address_line1": "Street address",
            "city": "City",
            "state": "State",
            "postal_code": "Zip code",
            "accepting_new_patients": true/false/null,
            "telehealth": true/false/null,
            "languages": ["Language 1", "Language 2"],
            "overall_confidence": 0.0 to 1.0
        }
        """

    def enrich_profile(self, partial_profile: dict):
        # 1. SETUP SEARCH (Python Logic)
        name = f"{partial_profile.get('first_name')} {partial_profile.get('last_name')}"
        location = f"{partial_profile.get('city')} {partial_profile.get('state')}"
        
        # We define a few high-precision queries
        queries = [
            f"{name} {location} official profile",
            f"{name} NPI registry",
            f"{name} {location} practice location"
        ]

        collected_context = []
        driver = None
        
        try:
            # 2. GATHER DATA with FRESH DRIVER
            driver = create_driver()
            
            seen_urls = set()
            for q in queries:
                if not driver: break 
                
                urls = search_web_with_driver(driver, q)
                # We only take the top 1-2 results per query to keep the prompt clean for 8B
                for url in urls[:2]: 
                    if url in seen_urls: continue
                    seen_urls.add(url)
                    
                    content = scrape_webpage_with_driver(driver, url)
                    if content:
                        # We inject the Source URL so the LLM can fill the 'website' field
                        collected_context.append(f"SOURCE_URL: {url}\nPAGE_CONTENT: {content}\n---")
                        
        except Exception as e:
            print(f"Driver/Search Error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except: pass

        full_context = "\n".join(collected_context)
        
        # 3. EXTRACTION (The Intelligence)
        user_prompt = f"""
        TARGET ENTITY: {name}, {partial_profile.get('credential')}
        LOCATION: {location}
        KNOWN NPI: {partial_profile.get('npi')}

        BELOW IS THE SCRAPED TEXT FROM THE WEB. FILL THE JSON SCHEMA BASED ON THIS TEXT.
        
        {full_context}
        """

        print(f"\n--> Extracting expanded schema for {name} using Groq...")
        
        try:
            # Combine system and user prompt for Groq as simple message list or concatenated
            # groq_client handles "messages" list.
            full_prompt = f"SYSTEM INSTRUCTIONS:\n{self.system_prompt}\n\nUSER REQUEST:\n{user_prompt}"
            
            response_content = generate_text(
                prompt=full_prompt, 
                json_mode=True,
                model="llama-3.3-70b-versatile"
            )
            return response_content
            
        except Exception as e:
            return json.dumps({"error": str(e), "overall_confidence": 0.0})

if __name__ == "__main__":
    manager = EnrichmentManager()

    incomplete_profile = {
        "first_name": "SATYASREE",
        "last_name": "UPADHYAYULA",
        "credential": "MD",
        "city": "Saint Louis",
        "state": "Missouri (MO)",
        "npi": "1891106191"
    }

    try:
        print("--- Starting Pipeline Enrichment ---")
        result_json = manager.enrich_profile(incomplete_profile)
        print("\n--- FINAL ENRICHED PROFILE ---")
        print(json.dumps(json.loads(result_json), indent=2))
    except Exception as e:
        print(f"Error: {e}")