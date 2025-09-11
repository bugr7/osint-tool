import os
import platform
import time
import threading
from colorama import Fore, Back, init, Style
import requests
import re

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


def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = f"https://html.duckduckgo.com/html/?q={search_query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    links = []

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            found = re.findall(r'href="(https?://[^"]+)"', resp.text)
            for link in found:
                if "duckduckgo.com" not in link and link not in links:
                    links.append(link)
                if len(links) >= num_results:
                    break
        else:
            print(Fore.RED + f"[!] DuckDuckGo returned {resp.status_code}", flush=True)
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


def ask_yes_no(question, color=Fore.YELLOW):
    while True:
        answer = input(color + question + " (yes/no): " + Style.RESET_ALL).strip().lower()
        if answer in ("yes", "y"):
            return True
        elif answer in ("no", "n"):
            return False
        else:
            print(Fore.RED + "[!] Invalid input. Please answer 'yes' or 'no'.")


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
    print(Fore.GREEN + ascii_art + Fore.RED + "OSINT Tool - DuckDuckGo Multithreaded v0.4" + Fore.GREEN + "\n", flush=True)

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
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.", flush=True)
            continue

        # سؤال permission قبل البحث
        if not ask_yes_no("[?] Do you have permission to search this account?"):
            print(Fore.RED + "[!] Permission not confirmed. Exiting.", flush=True)
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
            time.sleep(REQUEST_DELAY)

        for t in threads:
            t.join()

        # إعادة البحث
        if not ask_yes_no("\n[?] Do you want to search again?"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋", flush=True)
            break


if __name__ == "__main__":
    main()
