# tool.py
import requests
from colorama import Fore, Style, init
import platform
import time

init(autoreset=True)

SERVER_URL = "https://osint-tool-production.up.railway.app/search"  # ضع هنا رابط سيرفرك على Railway

PLATFORMS = [
    "Facebook", "Instagram", "Youtube", "TikTok",
    "Snapchat", "Reddit", "Twitter", "Pinterest", "LinkedIn"
]

def fetch_results(identifier):
    payload = {"identifier": identifier}
    try:
        resp = requests.post(SERVER_URL, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            results_by_platform = {p: [] for p in PLATFORMS}
            for item in data:
                platform_name = item.get("platform")
                link = item.get("link")
                if platform_name in results_by_platform:
                    results_by_platform[platform_name].append(link)
            return results_by_platform
        else:
            print(Fore.RED + f"[!] Server returned status {resp.status_code}")
            return {p: [] for p in PLATFORMS}
    except Exception as e:
        print(Fore.RED + f"[!] API request failed: {e}")
        return {p: [] for p in PLATFORMS}

def display_results(results):
    for platform_name, links in results.items():
        count = len(links)
        print(Fore.YELLOW + f"🔍 {platform_name} - {count}/10")
        if links:
            for link in links[:10]:
                print(Fore.CYAN + f"   {link}")
        else:
            print(Fore.RED + "   No results found.")
        print(Fore.MAGENTA + "-"*50)

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
""" + Fore.RED + "OSINT Tool - Server API version 0.1" + Fore.GREEN + "\n")

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        while True:
            confirm = input(Fore.YELLOW + "[?] Do you have permission to search this account? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                break
            elif confirm in ("no", "n"):
                print(Fore.RED + "[!] Permission not confirmed. Exiting.")
                return
            else:
                print(Fore.RED + "[!] Invalid input. Please answer 'yes' or 'no'.")

        print(Fore.MAGENTA + f"\n🔍 Searching for: {identifier}\n")
        results = fetch_results(identifier)
        display_results(results)

        again = input(Fore.MAGENTA + "\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
