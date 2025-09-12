# tool.py
import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style
import time
import platform
import json
from datetime import datetime
import os

init(autoreset=True)

SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8080/log_search")

PLATFORMS = {
    "Facebook": "facebook.com",
    "Instagram": "instagram.com",
    "Youtube": "youtube.com",
    "TikTok": "tiktok.com",
    "Snapchat": "snapchat.com",
    "Reddit": "reddit.com",
    "Twitter": "twitter.com",
    "Pinterest": "pinterest.com",
    "LinkedIn": "linkedin.com",
}

REQUEST_DELAY = 0.5

def duckduckgo_search(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    headers = {"User-Agent": "Mozilla/5.0"}
    links = []
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = soup.select("a.result__a")
        for a in anchors:
            href = a.get("href")
            if href and "duckduckgo.com" not in href:
                links.append(href)
            if len(links) >= num_results:
                break
    except Exception as e:
        print(Fore.RED + f"⚠️ Error searching {site}: {e}")
    return links

def log_to_server(search_term):
    ip = "Unknown"
    os_name = platform.system() + " " + platform.release()
    timestamp = datetime.utcnow().isoformat()
    try:
        import requests
        ip = requests.get("https://api64.ipify.org?format=json", timeout=10).json().get("ip","Unknown")
    except:
        pass
    payload = {"search": search_term, "ip": ip, "os": os_name, "timestamp": timestamp}
    try:
        requests.post(SERVER_URL, json=payload, timeout=10)
    except:
        pass

def main():
    print(Fore.GREEN + "\nOSINT Tool - DuckDuckGo Scraper v1.0\n")
    print(Fore.WHITE + "🔎 Platforms covered: " + ", ".join(PLATFORMS.keys()) + "\n")

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        confirm = input(Fore.YELLOW + "[?] Do you have permission to search this account? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            print(Fore.RED + "[!] Permission not confirmed. Exiting.")
            break

        log_to_server(identifier)

        for platform_name, domain in PLATFORMS.items():
            print(Fore.MAGENTA + f"\n🔍 Searching {platform_name}...")
            links = duckduckgo_search(identifier, domain)
            if links:
                print(Fore.GREEN + f"{platform_name} - {len(links)}/10 results:")
                for link in links:
                    print(Fore.CYAN + f"   {link}")
            else:
                print(Fore.RED + f"{platform_name} - 0/10 No results found.")
            time.sleep(REQUEST_DELAY)

        again = input(Fore.MAGENTA + "\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
