import requests
from bs4 import BeautifulSoup
import urllib.parse

def ddg_search(query, platform, limit=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/117.0 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={query}+site:{platform}.com"

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"[!] خطأ في DuckDuckGo: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for a in soup.select("a.result__a"):
        href = a.get("href")
        if href and "uddg=" in href:
            # نفك الرابط الأصلي من الوسيط "uddg"
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if "uddg" in parsed:
                real_url = parsed["uddg"][0]
                if platform in real_url:
                    results.append(real_url)
        if len(results) >= limit:
            break

    return results


def osint_tool(name_or_username):
    platforms = ["youtube", "tiktok", "reddit", "linkedin", "facebook", "instagram"]

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
