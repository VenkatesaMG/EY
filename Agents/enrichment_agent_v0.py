import os
import atexit
import time
import json
from dotenv import load_dotenv
import ollama

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

# --- KEEPING YOUR EXISTING DRIVER SETUP ---
_driver_instance = None

def get_shared_driver():
    global _driver_instance
    if _driver_instance is None:
        print("--- LAUNCHING CHROME ---")
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        service = Service(ChromeDriverManager().install())
        _driver_instance = webdriver.Chrome(service=service, options=options)
        atexit.register(cleanup_driver)
    return _driver_instance

def cleanup_driver():
    global _driver_instance
    if _driver_instance:
        try:
            _driver_instance.quit()
        except:
            pass
        _driver_instance = None

# --- MODIFIED SEARCH & SCRAPE TOOLS ---
# We return the data directly instead of printing it for the Agent to "see"

def search_web_direct(query: str):
    driver = get_shared_driver()
    urls = []
    try:
        print(f"DEBUG: Searching DuckDuckGo for '{query}'...")
        driver.get(f"https://html.duckduckgo.com/html/?q={query}")
        time.sleep(2)
        elements = driver.find_elements(By.CSS_SELECTOR, ".result")
        for el in elements[:3]: # Limit to top 3 to save context
            try:
                link_el = el.find_element(By.CSS_SELECTOR, "a.result__a")
                urls.append(link_el.get_attribute("href"))
            except: continue
    except Exception as e:
        print(f"Search Error: {e}")
    return urls

def scrape_webpage_direct(url: str):
    driver = get_shared_driver()
    try:
        print(f"DEBUG: Scraping {url}...")
        driver.get(url)
        time.sleep(1)
        body = driver.find_element(By.TAG_NAME, "body").text
        # Clean up excessive newlines to save tokens
        clean_body = " ".join(body.split())
        return clean_body[:3000] # Limit chars per page
    except Exception as e:
        print(f"Scrape Error: {e}")
        return ""

class EnrichmentManager:
    def __init__(self):
        self.model = "qwen2.5:7b"
        
        
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
        
        # 2. GATHER DATA (The "Grunt Work")
        # (Assuming search_web_direct and scrape_webpage_direct are defined as in previous turn)
        seen_urls = set()
        for q in queries:
            urls = search_web_direct(q)
            # We only take the top 1-2 results per query to keep the prompt clean for 8B
            for url in urls[:2]: 
                if url in seen_urls: continue
                seen_urls.add(url)
                
                content = scrape_webpage_direct(url)
                if content:
                    # We inject the Source URL so the LLM can fill the 'website' field
                    collected_context.append(f"SOURCE_URL: {url}\nPAGE_CONTENT: {content}\n---")

        full_context = "\n".join(collected_context)
        
        # 3. EXTRACTION (The Intelligence)
        user_prompt = f"""
        TARGET ENTITY: {name}, {partial_profile.get('credential')}
        LOCATION: {location}
        KNOWN NPI: {partial_profile.get('npi')}

        BELOW IS THE SCRAPED TEXT FROM THE WEB. FILL THE JSON SCHEMA BASED ON THIS TEXT.
        
        {full_context}
        """

        print(f"\n--> Extracting expanded schema for {name}...")
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self.system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                format="json" # Forces valid JSON output
            )
            return response['message']['content']
            
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
    finally:
        cleanup_driver()