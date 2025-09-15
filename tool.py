import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

def ddg_search(query, platform, limit=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/117.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://duckduckgo.com/"
    }
    url = f"https://duckduckgo.com/html/?q={query}+site:{platform}.com"

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"[!] خطأ في الطلب: {e}")
        return []

    if response.status_code != 200:
        print(f"[!] خطأ في DuckDuckGo: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for a in soup.select("a.result__a"):
        href = a.get("href")
        if not href:
            continue

        # DuckDuckGo يعطينا redirect فيه ?uddg=... → نفكك الرابط
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

    time.sleep(1)  # نرتاح شوية بين كل طلب
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
