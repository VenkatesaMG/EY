"""
Test script for finding an organization's official website domain.
Searches DuckDuckGo for "{org_name} official website" and prints the top 5 domains.
"""

import time
from urllib.parse import urlparse, parse_qs, unquote

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def find_org_domains(org_name: str):
    """
    Search for '{org_name} official website' on DuckDuckGo
    and return the top 5 result domains with their full URLs.
    """
    driver = None
    try:
        driver = create_driver()
        query = f"{org_name} official website"
        print(f"\n🔍 Searching DuckDuckGo for: '{query}'\n")
        print("=" * 60)

        driver.get(f"https://html.duckduckgo.com/html/?q={query}")
        time.sleep(3)

        elements = driver.find_elements(By.CSS_SELECTOR, ".result")
        
        results = []
        for i, el in enumerate(elements[:5]):
            try:
                link_el = el.find_element(By.CSS_SELECTOR, "a.result__a")
                url = link_el.get_attribute("href")
                title = link_el.text

                # Unwrap DuckDuckGo redirect URLs (can be nested)
                for _ in range(3):
                    parsed_check = urlparse(url)
                    if "duckduckgo.com" in parsed_check.netloc:
                        qs = parse_qs(parsed_check.query)
                        if "uddg" in qs:
                            url = unquote(qs["uddg"][0])
                        else:
                            break
                    else:
                        break

                # Skip ad/tracker URLs that couldn't be fully unwrapped
                parsed_final = urlparse(url)
                if any(ad in parsed_final.netloc.lower() for ad in ['duckduckgo.com', 'bing.com/aclick', 'spokeo.com']):
                    continue

                domain = parsed_final.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]

                results.append({
                    "rank": i + 1,
                    "title": title,
                    "url": url,
                    "domain": domain
                })
            except Exception:
                continue

        if not results:
            print("❌ No results found!")
            return

        for r in results:
            print(f"  #{r['rank']}  📌 Domain:  {r['domain']}")
            print(f"       Title:   {r['title']}")
            print(f"       URL:     {r['url']}")
            print()

        print("=" * 60)
        print(f"\n✅ Top domain pick: {results[0]['domain']}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    # --- Change the org name here to test ---
    org_name = "The Emory Clinic Inc"

    print(f"\n{'=' * 60}")
    print(f"  DOMAIN FINDER TEST — Org: '{org_name}'")
    print(f"{'=' * 60}")

    find_org_domains(org_name)
