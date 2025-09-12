# tool.py
import platform
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

SERVER_URL = os.getenv("RAILWAY_SERVER_URL")

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

REQUEST_DELAY = 1.5
MAX_RESULTS = 10
MAX_RETRIES = 8  # رفع عدد المحاولات لتقليل فقدان النتائج

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def log_user_search(search_text):
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=10).json().get("ip", "0.0.0.0")
    except Exception:
        ip = "0.0.0.0"

    data = {
        "username": platform.node(),
        "os": platform.system() + " " + platform.release(),
        "country": "Unknown",
        "ip": ip,
        "search": search_text
    }

    try:
        requests.post(SERVER_URL, json=data, timeout=15)
    except Exception as e:
        print("⚠️ Failed to log user search:", e)


def duckduckgo_search(query, site=None, max_results=MAX_RESULTS):
    """بحث في DuckDuckGo مع Retry محسّن"""
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    links = []

    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=25)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                anchors = soup.select("a.result__a")
                if not anchors:
                    anchors = soup.find_all("a")
                for a in anchors:
                    href = a.get("href")
                    link = None
                    if href:
                        if "uddg=" in href:
                            m = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg")
                            if m:
                                link = urllib.parse.unquote(m[0])
                        else:
                            link = href

                    if link and link.startswith("http") and "duckduckgo.com" not in link and link not in links:
                        links.append(link)
                    if len(links) >= max_results:
                        break
                if links:
                    return links
            elif resp.status_code in (202, 429):
                wait = (attempt + 1) * 3  # زيادة الوقت تدريجيًا
                print(f"⚠️ DuckDuckGo {resp.status_code}, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue
            else:
                print(f"❌ DuckDuckGo returned status: {resp.status_code}")
                break
        except Exception as e:
            print("⚠️ DuckDuckGo request error:", e)
            time.sleep(2)

    return links


def search_identifier(identifier):
    results_total = []

    for platform_name, domain in PLATFORMS.items():
        print(f"🔍 Searching {platform_name}...")
        try:
            links = duckduckgo_search(identifier, site=domain)
            count = len(links)
            print(f"✅ {platform_name}: {count}/{MAX_RESULTS}")
            for link in links:
                print(f"   {link}")
                results_total.append({"platform": platform_name, "link": link})
        except Exception as e:
            print(f"⚠️ Error searching {platform_name}: {e}")
        time.sleep(REQUEST_DELAY)

    return results_total


def main():
    while True:
        identifier = input("[?] Enter username or first/last name: ").strip()
        if not identifier:
            print("❌ No input provided.")
            continue

        log_user_search(identifier)
        search_identifier(identifier)

        again = input("\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print("✔ Exiting.")
            break


if __name__ == "__main__":
    main()

