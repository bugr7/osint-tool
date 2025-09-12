# tool.py
import platform
import time
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init

init(autoreset=True)

# ===== إعداد Turso Logs =====
TURSO_API_URL = "https://osint-tool-production.up.railway.app/log"  # نقطة إرسال الـ log

# ===== منصات =====
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

# ===== DuckDuckGo search =====
def duckduckgo_search(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    links = []
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            anchors = soup.select("a.result__a")
            if not anchors:
                anchors = soup.find_all("a")
            for a in anchors:
                href = a.get("href")
                if href and "duckduckgo.com" not in href and href.startswith("http"):
                    if href not in links:
                        links.append(href)
                    if len(links) >= num_results:
                        break
    except Exception as e:
        print(Fore.RED + f"⚠️ Error searching {site}: {e}")
    return links

# ===== إرسال Log إلى Turso =====
def send_log(search_query):
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=10).json().get("ip", "Unknown")
    except:
        ip = "Unknown"
    payload = {
        "username": platform.node(),
        "os": platform.system() + " " + platform.release(),
        "country": "Unknown",
        "ip": ip,
        "search": search_query
    }
    try:
        requests.post(TURSO_API_URL, json=payload, timeout=10)
    except:
        pass  # إذا فشل إرسال log، نتجاهله

# ===== عرض النتائج =====
def print_platform_frame(platform_name, links):
    header = f"{platform_name} - {len(links)}/10"
    top = "╭─ " + header + " ─╮"
    bottom = "╰" + "─" * (len(top) - 2) + "╯"
    print(Fore.BLUE + top + Style.RESET_ALL)
    if links:
        for link in links:
            print(Fore.CYAN + f"   {link}")
    else:
        print(Fore.RED + "   No results found.")
    print(Fore.BLUE + bottom + Style.RESET_ALL + "\n")

# ===== البرنامج الرئيسي =====
def main():
    print(Fore.GREEN + "OSINT Tool - Local DuckDuckGo Search + Turso Logs\n")

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        confirm = input(Fore.YELLOW + "[?] Do you have permission to search this account? (yes/no): " + Style.RESET_ALL).strip().lower()
        if confirm not in ("yes", "y"):
            print(Fore.RED + "[!] Permission not confirmed. Exiting.")
            continue

        # إرسال Log فقط
        send_log(identifier)

        # البحث في كل منصة
        for platform_name, domain in PLATFORMS.items():
            links = duckduckgo_search(identifier, domain)
            print_platform_frame(platform_name, links)
            time.sleep(REQUEST_DELAY)

        again = input(Fore.MAGENTA + "[?] Search again? (yes/no): " + Style.RESET_ALL).strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "[✔] Exiting OSINT Tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
