import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style
import platform
import time

init(autoreset=True)

# ===== المنصات =====
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

# ===== البحث في Yandex =====
def search_yandex(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = f"https://yandex.com/search/?text={search_query.replace(' ', '+')}&search_source=yacom_desktop_common"
    links = []
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.Link.Link_theme_normal")[:num_results]:
            href = a.get("href")
            if href and href.startswith("http"):
                links.append(href)
    except Exception as e:
        print(Fore.RED + f"⚠️ Error searching {site}: {e}")
    return links

# ===== عرض النتائج =====
def run_checks(identifier):
    print(Fore.MAGENTA + "\n" + "="*60)
    print(Fore.MAGENTA + f"🔍 Start search about: {identifier}")
    print(Fore.MAGENTA + "="*60 + "\n")

    for platform_name, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"🔍 Searching {platform_name}...")
        links = search_yandex(identifier, domain)
        count = len(links)
        print(Fore.GREEN + f"✅ {platform_name}: {count}/10")

        if links:
            for link in links:
                print(Fore.CYAN + f"   {link}")
        else:
            print(Fore.RED + "   No results found.")

        print(Fore.MAGENTA + "-"*60 + "\n")
        time.sleep(REQUEST_DELAY)

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
""" + Fore.RED + "OSINT Tool - Yandex version 0.1" + Fore.GREEN + "\n")

    print(Fore.WHITE + "🔎 Platforms covered: Facebook, Instagram, Youtube, TikTok, Snapchat, Reddit, Twitter, Pinterest, LinkedIn\n")

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        run_checks(identifier)

        again = input(Fore.MAGENTA + "\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
