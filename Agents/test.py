import os
import atexit
import time
import json
from dotenv import load_dotenv
import ollama  # We use the native library instead of LangChain

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

# --- 1. SETUP SELENIUM (SHARED DRIVER) ---
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

# --- 2. DEFINE TOOLS (Plain Python Functions) ---

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
        for i, el in enumerate(elements[:3]):
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

# Map string names to functions for the execution loop
# available_functions = {
#     'search_web': search_web,
#     'scrape_webpage': scrape_webpage
# }

# --- 3. THE NATIVE AGENT LOOP ---

# class EnrichmentManager:
#     def __init__(self):
#         self.model = "llama3.1"
#         self.system_prompt = """You are an expert Healthcare Enrichment Agent.
#         Your goal is to find missing details (Phone, Fax, Address) for a provider.
        
#         INSTRUCTIONS:
#         1. Always SEARCH first using 'search_web'.
#         2. If you see a profile link (NPI Registry, Healthgrades, etc), you MUST 'scrape_webpage' on that URL.
#         3. Do not assume data; verify it by scraping.
#         4. Once you have the data, output the Final JSON.
#         """

#     def enrich_profile(self, partial_profile: dict, missing_keys: list):
#         # Construct the user request
#         user_query = (
#             f"Find missing details for:\n"
#             f"Name: {partial_profile.get('first_name')} {partial_profile.get('last_name')}, {partial_profile.get('credential')}\n"
#             f"Location: {partial_profile.get('city')}, {partial_profile.get('state')}\n"
#             f"NPI: {partial_profile.get('npi')}\n\n"
#             f"FIND THESE MISSING KEYS: {missing_keys}\n"
#         )

#         messages = [
#             {'role': 'system', 'content': self.system_prompt},
#             {'role': 'user', 'content': user_query}
#         ]

#         # Loop for a max of 10 turns (prevents infinite loops)
#         for _ in range(10):
#             # 1. Ask LLM
#             response = ollama.chat(
#                 model=self.model,
#                 messages=messages,
#                 tools=[search_web, scrape_webpage] # Pass actual functions
#             )
            
#             msg = response['message']
#             messages.append(msg) # Add assistant reply to history

#             # 2. Check if LLM wants to use tools
#             if msg.get('tool_calls'):
#                 print(f"--> Agent decided to use {len(msg['tool_calls'])} tool(s)...")
                
#                 for tool in msg['tool_calls']:
#                     fn_name = tool['function']['name']
#                     args = tool['function']['arguments']
                    
#                     # Execute tool
#                     if fn_name in available_functions:
#                         function_to_call = available_functions[fn_name]
#                         tool_output = function_to_call(**args)
                        
#                         # Add tool output to history
#                         messages.append({
#                             'role': 'tool',
#                             'content': str(tool_output),
#                         })
#                     else:
#                         print(f"Error: Function {fn_name} not found")
#             else:
#                 # 3. No tools used? This is the final answer.
#                 return msg['content']
                
#         return "Agent timed out after 10 steps."

if __name__ == "__main__":
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

    response = search_web("SATYASREE UPADHYAYULA 1891106191")
    print(response)