#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style
import random, time

# ===== Colors Init =====
init(autoreset=True)

# ===== Banner =====
banner = r"""
 /$$$$$$$                                   /$$$$$$$$
| $$__  $$                                 |_____ $$/ 
| $$  \ $$ /$$   /$$  /$$$$$$         /$$$$$$   /$$/  
| $$$$$$$/| $$  | $$ /$$__  $$ /$$$$$$|____  $$ /$$/   
| $$__  $$| $$  | $$| $$  \__/|______/ /$$$$$$$| $$    
| $$  \ $$| $$  | $$| $$       /$$    /$$__  $$| $$    
| $$  | $$|  $$$$$$/| $$      | $$   |  $$$$$$$| $$    
|__/  |__/ \______/ |__/      |__/    \_______/|__/    
"""
print(banner)
print(Fore.CYAN + "[*] DuckDuckGo OSINT Tool - Platforms Links\n")

# ===== Platforms =====
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

# ===== Fake User-Agents =====
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 Version/16.0 Safari/605.1.15",
]

# ===== DuckDuckGo Search =====
session = requests.Session()

def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    try:
        resp = session.post(url, data=params, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.select(".result__a")[:num_results]:
            title = a.get_text()
            link = a.get("href")
            results.append({"title": title, "href": link})
        return results
    except Exception as e:
        print(Fore.RED + f"[!] Error while searching: {e}")
        return []

# ===== Run Checks =====
def run_checks(identifier):
    print(Fore.MAGENTA + "\n" + "="*60)
    print(Fore.MAGENTA + f"🔍 Searching for: {identifier}")
    print(Fore.MAGENTA + "="*60 + "\n")

    for platform_name, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"🔍 {platform_name} ...")
        links = duckduckgo_search_links(identifier, domain, num_results=10)
        count = len(links)
        print(Fore.GREEN + f"✅ {platform_name}: {count}/10")

        if links:
            for idx, link in enumerate(links, 1):
                print(Fore.CYAN + f"   {idx}. {link['title']}")
                print(Fore.WHITE + f"      {link['href']}")
        else:
            print(Fore.RED + "   No results.")

        print(Fore.MAGENTA + "-"*60 + "\n")
        time.sleep(2)  # prevent temporary block

# ===== Main =====
def main():
    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or full name (exit to quit): " + Style.RESET_ALL).strip()
        if identifier.lower() == "exit":
            print(Fore.GREEN + "[✔] Exiting tool. 👋")
            break
        run_checks(identifier)

if __name__ == "__main__":
    main()
