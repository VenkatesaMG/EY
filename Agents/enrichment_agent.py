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

def search_web(query: str):
    """
    Search DuckDuckGo (HTML Version). 
    Returns top 3 results with titles and specific URLs.
    Args:
        query: The search string (e.g. 'Dr. Smith NPI registry')
    """
    driver = get_shared_driver()
    results_text = ""
    try:
        print(f"\nDEBUG: Searching DuckDuckGo for '{query}'...")
        driver.get(f"https://html.duckduckgo.com/html/?q={query}")
        time.sleep(2)
        elements = driver.find_elements(By.CSS_SELECTOR, ".result")
        print(elements)
        for i, el in enumerate(elements[:5]):
            try:
                link_el = el.find_element(By.CSS_SELECTOR, "a.result__a")
                link = link_el.get_attribute("href")
                title = link_el.text
                results_text += f"RESULT {i+1}: [Title: {title}] (URL: {link})\n"
            except: continue
    except Exception as e:
        return f"Search Error: {e}"
        
    return results_text if results_text else "No results found."

def scrape_webpage(url: str):
    """
    Deep scrape a specific URL. Returns text content.
    Args:
        url: The full http url to scrape.
    """
    driver = get_shared_driver()
    try:
        print(f"DEBUG: Scraping {url}...")
        driver.get(url)
        time.sleep(2)
        body = driver.find_element(By.TAG_NAME, "body").text
        return f"PAGE CONTENT:\n{body[:4000]}..." 
    except Exception as e:
        return f"Scrape Error: {e}"

available_functions = {
    'search_web': search_web,
    'scrape_webpage': scrape_webpage
}

class EnrichmentManager:
    def __init__(self):
        self.model = "qwen2.5:7b"
        self.system_prompt = """
        You are the **Lead Forensic Data Enrichment Agent** for a major Insurance Firm. 
    Your mission is to construct a **"Golden Record"** profile for the requested Provider (Individual or Organization) by searching, scraping, and fusing information from the web.

    **PRIORITY FIELDS (Critical for Payer Enrollment):**
    1. **Identity**: NPI (10-digit), Full Legal Name, Taxonomy Codes.
    2. **Contact**: Verified Practice Address, Primary Phone, Primary Fax.
    3. **Affiliation**: Group Practice Name, Hospital Privileges, State License Numbers.

    ---

    ### STRATEGY & WORKFLOW (ReAct Loop)

    You must use the following thinking and execution loop to solve the user's request.

    **INSTRUCTIONS:**
    1.  **Search Initial**: Start by searching for `Provider Name + NPI + City`.
    2.  **Scrape Verification**: Immediately identify high-trust sources (NPI Registry, State Medical Board, Official Clinic Websites) from the search results. You **MUST** use the `scrape_webpage` tool on the most promising URL to verify the details.
    3.  **Source Fusion**: If you find conflicting data (e.g., two addresses or two phone numbers), search for a third, high-authority source (e.g., the official hospital directory) to resolve the conflict. **Do NOT stop** after one piece of data is found; ensure all missing fields are checked.

    ### CRITICAL EXTRACTION AND FUSION RULES

    These rules override generalized thinking and ensure accurate data capture from messy text:

    1.  **Aggressive Pattern Matching**:
        * **Phone/Fax**: If you see a number formatted like `(XXX) XXX-XXXX` or `XXX-XXX-XXXX` near an address or in a contact section, **capture it**. If a number is followed by 'F' or 'Fx', label it as 'Fax'. Assume any unlabeled ten-digit number near an address is the primary phone number.
        * **Address**: Capture the entire block of address text (Street, City, State, ZIP). Do not abbreviate city names.
    2.  **Contextual Inference**:
        * If the scraped page title or URL matches the Provider Name or Organization Name, **ALL contact details** on that page are inferred to belong to that entity.
    3.  **Ambiguity Handling (The Golden Rule)**:
        * If the scraped text provides **multiple distinct practice locations or phone numbers**, list all of them in a structured way within your final JSON. Do **NOT** choose one arbitrarily. *The organization may have multiple practice sites.*
    4.  **Final Consolidation**: After all searching is complete, merge **all verified data** into the final JSON structure. Unfound data points should be returned as `null`.

    ---

    **Use the following format:**
    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Observation can repeat N times)
    Thought: I have verified the necessary details across multiple high-trust sources and consolidated the profile.
    Final Answer: the final answer to the original input question (OUTPUT THE FINAL JSON ONLY)

    Question: {input}
    Thought:{agent_scratchpad}
        """

    def enrich_profile(self, partial_profile: dict, missing_keys: list):
        user_query = (
            f"Find missing details for:\n"
            f"Name: {partial_profile.get('first_name')} {partial_profile.get('last_name')}, {partial_profile.get('credential')}\n"
            f"Location: {partial_profile.get('city')}, {partial_profile.get('state')}\n"
            f"NPI: {partial_profile.get('npi')}\n\n"
            f"FIND THESE MISSING KEYS: {missing_keys}\n"
        )

        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': user_query}
        ]

        for _ in range(15):
            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=[search_web, scrape_webpage]
            )

            print(response)
            
            msg = response['message']
            messages.append(msg)

            if msg.get('tool_calls'):
                print(f"--> Agent decided to use {len(msg['tool_calls'])} tool(s)...")
                
                for tool in msg['tool_calls']:
                    fn_name = tool['function']['name']
                    args = tool['function']['arguments']
                    
                    if fn_name in available_functions:
                        function_to_call = available_functions[fn_name]
                        tool_output = function_to_call(**args)
                        
                        messages.append({
                            'role': 'tool',
                            'content': str(tool_output),
                        })
                    else:
                        print(f"Error: Function {fn_name} not found")
            else:
                return msg['content']
                
        return "Agent timed out after 10 steps."

if __name__ == "__main__":
    manager = EnrichmentManager()

    incomplete_profile = {
        "first_name": "SATYASREE",
        "last_name": "UPADHYAYULA",
        "credential": "MD",
        "city": "Saint Louis",
        "state": "Missouri (MO)",
        "npi": "1891106191",
        "phone" : None,
        "email" : None
    }

    try:
        print("--- Starting Deep Enrichment (Native Llama Mode) ---")
        final_response = manager.enrich_profile(
            partial_profile=incomplete_profile, 
            missing_keys=["phone", "practice_address", "fax"]
        )
        print("\n--- FINAL ENRICHED PROFILE ---")
        print(final_response)
    finally:
        cleanup_driver()