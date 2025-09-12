import platform
import time
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from colorama import Fore, init, Style
import os

init(autoreset=True)

SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:5000")
MAX_RETRIES = 5
REQUEST_DELAY = 3  # تأخير بين كل طلب لتقليل خطأ 202

PLATFORMS = {
    "Facebook":"facebook.com", "Instagram":"instagram.com", "Youtube":"youtube.com",
    "TikTok":"tiktok.com", "Snapchat":"snapchat.com", "Reddit":"reddit.com",
    "Twitter":"twitter.com", "Pinterest":"pinterest.com", "LinkedIn":"linkedin.com"
}

def post_log(data):
    try:
        requests.post(f"{SERVER_URL}/log_search", json=data, timeout=10)
    except:
        pass

def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    links = []

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                anchors = soup.select("a.result__a") or soup.find_all("a")
                for a in anchors:
                    href = a.get("href")
                    if href:
                        link = None
                        if "uddg=" in href:
                            m = re.search(r"uddg=([^&]+)", href)
                            if m:
                                link = urllib.parse.unquote(m.group(1))
                        else:
                            link = href
                        if link and link.startswith("http") and "duckduckgo.com" not in link and link not in links:
                            links.append(link)
                        if len(links) >= num_results:
                            break
                if links:
                    return links
            elif resp.status_code == 202:
                wait = REQUEST_DELAY * (attempt + 1)
                print(f"⚠️ DuckDuckGo 202, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue
        except:
            time.sleep(2)
    return links

def main():
    username = platform.node()
    os_name = platform.system() + " " + platform.release()
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=15).json()["ip"]
        country = requests.get(f"https://ipapi.co/{ip}/json/", timeout=15).json().get("country_name", "Unknown")
    except:
        ip, country = "0.0.0.0", "Unknown"

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            continue

        # إرسال البيانات فقط للسيرفر
        post_log({
            "username": username,
            "os": os_name,
            "country": country,
            "ip": ip,
            "search": identifier
        })

        print(Fore.MAGENTA + "\n🔍 Searching...\n")
        for platform_name, domain in PLATFORMS.items():
            print(Fore.YELLOW + f"🔍 Searching {platform_name}...")
            links = duckduckgo_search_links(identifier, site=domain, num_results=10)
            count = len(links)
            print(Fore.GREEN + f"✅ {count}/10 results:")
            if links:
                for l in links:
                    print(Fore.CYAN + f"   {l}")
            else:
                print(Fore.RED + "❌ No results found.")
            time.sleep(REQUEST_DELAY)

        again = input(Fore.MAGENTA + "\n[?] Search again? (yes/no): ").strip().lower()
        if again not in ("yes","y"):
            break

if __name__ == "__main__":
    main()
