import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

def get_headers():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
    ]
    return {
        "User-Agent": random.choice(agents),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://duckduckgo.com/"
    }

session = requests.Session()

def ddg_search(query, platform, limit=5):
    # أول طلب باش نجيب cookies
    session.get("https://duckduckgo.com/", headers=get_headers(), timeout=10)

    url = f"https://html.duckduckgo.com/html/?q={query}+site:{platform}.com"
    response = session.get(url, headers=get_headers(), timeout=10)

    if response.status_code != 200:
        print(f"[!] خطأ في DuckDuckGo: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for a in soup.select("a.result__a"):
        href = a.get("href")
        if not href:
            continue

        if "uddg=" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            real_url = qs.get("uddg", [None])[0]
            if real_url and platform in real_url:
                results.append(real_url)
        elif href.startswith("http") and platform in href:
            results.append(href)

        if len(results) >= limit:
            break

    time.sleep(1.5)
    return results


def osint_tool(name_or_username):
    platforms = ["youtube", "tiktok", "reddit", "linkedin"]

    for p in platforms:
        print(f"\n🔎 البحث في {p.capitalize()}...")
        results = ddg_search(name_or_username, p)
        if results:
            for r in results:
                print("👉", r)
        else:
            print("❌ لا توجد نتائج.")


if __name__ == "__main__":
    query = input("[?] أدخل الاسم واللقب أو اسم المستخدم: ")
    osint_tool(query)
