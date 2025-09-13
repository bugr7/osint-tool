# osint_tool_ddg_links_only_alpha_style.py

import platform
import time
from colorama import Fore, init, Style
from libsql_client import create_client_sync
from migrate import migrate
from duckduckgo_search import DDGS

init(autoreset=True)

# ===== إعداد Turso =====
DATABASE_URL = "https://search-osmoh.aws-eu-west-1.turso.io"  
AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NTc0MjkxNzEsImlkIjoiMGMwODllMjUtN2RiMC00Y2I1LWJhMDAtYWI1NTgxZjNjYjAxIiwicmlkIjoiYTM2YjJhZGQtNTU5NC00NDUxLThiY2EtZWRkNDgwZjI2ZWM0In0.4EdUBRRTA1uYTdGWnOP4jwnuFPZ6IrzuCBlzBdWtb31qw7B9vIX7rsiRZEUA6-Bf8hgcA-LaEkpPcl-r-csjCg"

client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
migrate(client)

client.execute("""
CREATE TABLE IF NOT EXISTS users_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    os TEXT,
    country TEXT,
    ip TEXT,
    search TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ===== منصات رئيسية =====
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
ddgs = DDGS()

# ===== البحث في DuckDuckGo =====
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
        print(Fore.RED + f"⚠️ Error searching {site}: {e}")
    return links

# ===== عرض النتائج بتصميم نسخة ألفا =====
def run_checks(identifier):
    print(Fore.MAGENTA + "\n" + "="*60)
    print(Fore.MAGENTA + f"🔍 Start search about: {identifier}")
    print(Fore.MAGENTA + "="*60 + "\n")

    for platform_name, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"🔍 Searching {platform_name}...")
        links = duckduckgo_search_links(identifier, domain)
        count = len(links)
        print(Fore.GREEN + f"✅ {platform_name}: {count}/10")

        if links:
            for link in links:
                print(Fore.CYAN + f"   {link}")
        else:
            print(Fore.RED + "   No results found.")

        print(Fore.MAGENTA + "-"*60 + "\n")

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
""" + Fore.RED + "OSINT Tool - DDGS Links Only version 0.1" + Fore.GREEN + "\n")

    print(Fore.WHITE + "🔎 Platforms covered: Facebook, Instagram, Youtube, TikTok, Snapchat, Reddit, Twitter, Pinterest, LinkedIn\n")

    try:
        import requests
        ip = requests.get("https://api64.ipify.org?format=json", timeout=15).json()["ip"]
        country = requests.get(f"https://ipapi.co/{ip}/json/", timeout=15).json().get("country_name", "Unknown")
    except:
        ip, country = "Unknown", "Unknown"

    username = platform.node()
    os_name = platform.system() + " " + platform.release()

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        client.execute(
            "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
            (username, os_name, country, ip, identifier)
        )

        while True:
            confirm = input(Fore.YELLOW + "[?] Do you have permission to search this account? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                break
            elif confirm in ("no", "n"):
                print(Fore.RED + "[!] Permission not confirmed. Exiting.")
                return
            else:
                print(Fore.RED + "[!] Invalid input. Please answer 'yes' or 'no'.")

        run_checks(identifier)

        again = input(Fore.MAGENTA + "\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
