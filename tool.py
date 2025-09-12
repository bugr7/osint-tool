# tool.py
import os
import platform
import time
import requests
from colorama import Fore, Back, Style, init

init(autoreset=True)

SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8080/log_search")
REQUEST_DELAY = 0.3

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

# ===== البحث في DuckDuckGo JSON API =====
def search_duckduckgo(query, site=None, max_results=10):
    search_query = f"{query} site:{site}" if site else query
    links = []
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": search_query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1,
            "skip_disambig": 1
        }
        resp = requests.get(url, params=params, timeout=15).json()
        if "RelatedTopics" in resp:
            for topic in resp["RelatedTopics"]:
                if "FirstURL" in topic:
                    links.append(topic["FirstURL"])
                elif "Topics" in topic:
                    for t in topic["Topics"]:
                        if "FirstURL" in t:
                            links.append(t["FirstURL"])
                if len(links) >= max_results:
                    break
    except Exception as e:
        print(Fore.RED + f"[!] Error searching {site}: {e}")
    return links[:max_results]

# ===== إرسال بيانات البحث للسيرفر =====
def log_search_to_server(query):
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=10).json().get("ip", "Unknown")
    except:
        ip = "Unknown"
    os_name = platform.system() + " " + platform.release()
    payload = {
        "query": query,
        "ip": ip,
        "os": os_name,
        "timestamp": int(time.time())
    }
    try:
        requests.post(SERVER_URL, json=payload, timeout=10)
    except:
        pass  # لا نكسر الأداة إذا السيرفر غير متاح

# ===== عرض النتائج =====
def print_platform_results(platform_name, links):
    header = f"{platform_name} - {len(links)}/10"
    print(Back.BLUE + Fore.WHITE + f"╭─ {header} ─╮" + Style.RESET_ALL)
    if links:
        for link in links:
            print(Fore.CYAN + f"   {link}")
    else:
        print(Fore.RED + "   No results found.")
    print(Back.BLUE + Fore.WHITE + "╰" + "─" * (len(header)+3) + "╯" + Style.RESET_ALL)
    print()

# ===== البرنامج الرئيسي =====
def main():
    print(Fore.GREEN + "OSINT Tool - DuckDuckGo JSON API Mode\n")
    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        confirm = input(Fore.YELLOW + "[?] Do you have permission to search this account? (yes/no): ").strip().lower()
        if confirm not in ("yes", "y"):
            print(Fore.RED + "[!] Permission not confirmed. Exiting.")
            return

        # إرسال بيانات البحث للسيرفر
        log_search_to_server(identifier)

        # البحث في كل منصة
        for platform_name, domain in PLATFORMS.items():
            links = search_duckduckgo(identifier, domain)
            print_platform_results(platform_name, links)
            time.sleep(REQUEST_DELAY)

        again = input(Fore.MAGENTA + "[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
