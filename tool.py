# tool.py
import os
import time
from colorama import Fore, Back, init, Style
import requests

init(autoreset=True)

# ===== رابط السيرفر =====
API_URL = os.getenv("API_URL", "https://osint-tool-production.up.railway.app/search")

PLATFORMS = {
    "Facebook": Back.BLUE,
    "Instagram": Back.MAGENTA,
    "Youtube": Back.RED,
    "TikTok": Back.CYAN,
    "Snapchat": Back.YELLOW,
    "Reddit": Back.LIGHTRED_EX,
    "Twitter": Back.LIGHTBLUE_EX,
    "Pinterest": Back.LIGHTMAGENTA_EX,
    "LinkedIn": Back.LIGHTCYAN_EX,
}

REQUEST_DELAY = 0.3

def search_via_api(identifier):
    """إرسال ما كتبه المستخدم للسيرفر واسترجاع النتائج"""
    try:
        response = requests.post(API_URL, json={"identifier": identifier}, timeout=25)
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"[!] API request failed: {e}", flush=True)
        return []

    if response.status_code == 200:
        try:
            return response.json()
        except Exception as e:
            print(Fore.RED + f"[!] Failed parsing API JSON: {e}", flush=True)
            return []
    else:
        print(Fore.RED + f"[!] API returned status {response.status_code}", flush=True)
        try:
            print(f"API text (start): {response.text[:400]}")
        except Exception:
            pass
        return []

def print_platform_frame(platform_name, links, color_bg):
    header = f"{platform_name} - {len(links)}/10"
    top = "╭─ " + header + " ─╮"
    bottom = "╰" + "─" * (len(top) - 2) + "╯"
    print(color_bg + Fore.WHITE + top + Style.RESET_ALL, flush=True)
    if links:
        for link in links[:10]:
            print(Fore.CYAN + f"   {link}", flush=True)
    else:
        print(Fore.RED + "   No results found.", flush=True)
    print(color_bg + Fore.WHITE + bottom + Style.RESET_ALL, flush=True)
    print(flush=True)

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
    print(Fore.GREEN + ascii_art + Fore.RED + "OSINT Tool - API Mode v2.0" + Fore.GREEN + "\n", flush=True)
    print(Fore.WHITE + "🔎 Platforms covered: Facebook, Instagram, Youtube, TikTok, Snapchat, Reddit, Twitter, Pinterest, LinkedIn\n", flush=True)

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.", flush=True)
            continue

        if not ask_yes_no("[?] Do you have permission to search this account?"):
            print(Fore.RED + "[!] Permission not confirmed. Exiting.", flush=True)
            continue

        api_results = search_via_api(identifier)
        print(Fore.GREEN + f"[✔] Fetched {len(api_results)} results from API.", flush=True)

        for platform_name, color_bg in PLATFORMS.items():
            links = [r["link"] for r in api_results if r.get("platform") == platform_name]
            print_platform_frame(platform_name, links, color_bg)
            time.sleep(REQUEST_DELAY)

        if not ask_yes_no("\n[?] Do you want to search again?"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋", flush=True)
            break

if __name__ == "__main__":
    main()
