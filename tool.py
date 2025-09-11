import os
import platform
import time
import threading
from colorama import Fore, Back, init, Style
import requests
from ddgs import DDGS

init(autoreset=True)

API_URL = os.getenv("API_URL", "https://osint-tool-production.up.railway.app/search")

PLATFORMS = {
    "Facebook": ("facebook.com", Back.BLUE),
    "Instagram": ("instagram.com", Back.MAGENTA),
    "Youtube": ("youtube.com", Back.RED),
    "TikTok": ("tiktok.com", Back.CYAN),
    "Snapchat": ("snapchat.com", Back.YELLOW),
    "Reddit": ("reddit.com", Back.LIGHTRED_EX),
    "Twitter": ("twitter.com", Back.LIGHTBLUE_EX),
    "Pinterest": ("pinterest.com", Back.LIGHTMAGENTA_EX),
    "LinkedIn": ("linkedin.com", Back.LIGHTCYAN_EX),
}

REQUEST_DELAY = 0.3
ddgs = DDGS()


def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    links = []
    try:
        results = ddgs.text(search_query, max_results=num_results)
        for r in results:
            if "href" in r and r["href"]:
                links.append(r["href"])
            if len(links) >= num_results:
                break
    except Exception as e:
        print(Fore.RED + f"⚠️ Error searching {site}: {e}", flush=True)
    return links


def search_via_api(identifier):
    try:
        response = requests.post(API_URL, json={"identifier": identifier}, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(Fore.RED + f"[!] API returned status {response.status_code}", flush=True)
            return []
    except Exception as e:
        print(Fore.RED + f"[!] API request failed: {e}", flush=True)
        return []


def print_platform_frame(platform_name, links, color_bg):
    header = f"{platform_name} - {len(links)}/10"
    top = "╭─ " + header + " ─╮"
    bottom = "╰" + "─" * (len(top) - 2) + "╯"
    print(color_bg + Fore.WHITE + top + Style.RESET_ALL, flush=True)
    if links:
        for link in links:
            print(Fore.CYAN + f"   {link}", flush=True)
    else:
        print(Fore.RED + "   No results found.", flush=True)
    print(color_bg + Fore.WHITE + bottom + Style.RESET_ALL, flush=True)
    print(flush=True)


def fetch_and_print(identifier, platform_name, domain, color_bg):
    links = duckduckgo_search_links(identifier, domain)
    print_platform_frame(platform_name, links, color_bg)


def main():
    print(Fore.GREEN + """
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
""" + Fore.RED + "OSINT Tool - DDGS Multithreaded v0.3" + Fore.GREEN + "\n", flush=True)

    print(Fore.WHITE + "🔎 Platforms covered: Facebook, Instagram, Youtube, TikTok, Snapchat, Reddit, Twitter, Pinterest, LinkedIn\n", flush=True)

    # الحصول على IP و Country
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=15).json()["ip"]
        country = requests.get(f"https://ipapi.co/{ip}/json/", timeout=15).json().get("country_name", "Unknown")
    except:
        ip, country = "Unknown", "Unknown"

    username = platform.node()
    os_name = platform.system() + " " + platform.release()

    while True:
        print(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL, end='', flush=True)
        identifier = input().strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.", flush=True)
            continue

        # جلب البيانات عبر API
        api_results = search_via_api(identifier)
        print(Fore.GREEN + f"[✔] Fetched {len(api_results)} results from API.", flush=True)

        # multithreading لكل منصة
        threads = []
        for platform_name, (domain, color_bg) in PLATFORMS.items():
            t = threading.Thread(target=fetch_and_print, args=(identifier, platform_name, domain, color_bg))
            threads.append(t)
            t.start()
            time.sleep(REQUEST_DELAY)  # قليل من التأخير لتجنب حظر DDG

        for t in threads:
            t.join()

        # إعادة البحث
        print(Fore.MAGENTA + "\n[?] Do you want to search again? (yes/no): " + Style.RESET_ALL, end='', flush=True)
        again = input().strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋", flush=True)
            break


if __name__ == "__main__":
    main()
