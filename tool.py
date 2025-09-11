import os
import time
from colorama import Fore, Back, init, Style
import requests

init(autoreset=True)

API_URL = os.getenv("API_URL", "https://osint-tool-production.up.railway.app/search")

# ===== منصات مع ألوان الإطارات =====
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

def print_platform_frame(platform_name, links, color_bg):
    header = f"{platform_name} - {len(links)} links"
    top = "╭─ " + header + " ─╮"
    bottom = "╰" + "─" * (len(top) - 2) + "╯"
    print(color_bg + Fore.WHITE + top + Style.RESET_ALL)
    if links:
        for link in links:
            print(Fore.CYAN + f"   {link}")
    else:
        print(Fore.RED + "   No results found.")
    print(color_bg + Fore.WHITE + bottom + Style.RESET_ALL)
    print()

def search_via_api(identifier):
    try:
        response = requests.post(API_URL, json={"identifier": identifier}, timeout=20)
        if response.status_code == 200:
            return response.json()
        else:
            print(Fore.RED + f"[!] API returned status {response.status_code}")
            return []
    except Exception as e:
        print(Fore.RED + f"[!] API request failed: {e}")
        return []

# ===== البرنامج الرئيسي =====
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
""" + Fore.RED + "OSINT Tool - API Results Design v0.3" + Fore.GREEN + "\n")

    print(Fore.WHITE + "🔎 Platforms covered: Facebook, Instagram, Youtube, TikTok, Snapchat, Reddit, Twitter, Pinterest, LinkedIn\n")

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        results = search_via_api(identifier)
        print(Fore.GREEN + f"[✔] Fetched {len(results)} total links from API.\n")

        # تجميع الروابط حسب المنصة
        platform_links = {name: [] for name in PLATFORMS.keys()}
        for item in results:
            platform = item.get("platform")
            link = item.get("link")
            if platform in platform_links and link:
                platform_links[platform].append(link)

        # طباعة كل منصة بالتصميم
        for platform_name, color_bg in PLATFORMS.items():
            links = platform_links.get(platform_name, [])
            print_platform_frame(platform_name, links, color_bg)
            time.sleep(REQUEST_DELAY)

        # سؤال إعادة البحث
        again = input(Fore.MAGENTA + "\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
