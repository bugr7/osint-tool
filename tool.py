import requests
from bs4 import BeautifulSoup
import time, random

def ddg_search(query, platform, limit=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/117.0 Safari/537.36"
    }
    url = f"https://lite.duckduckgo.com/lite/?q={query}+site:{platform}.com"

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        print(f"[!] خطأ في الاتصال: {e}")
        return []

    if response.status_code != 200:
        print(f"[!] خطأ في DuckDuckGo: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if platform in href and href.startswith("http"):
            results.append(href)
        if len(results) >= limit:
            break

    return results


def osint_tool(name_or_username):
    # زدت فيسبوك و انستقرام
    platforms = ["youtube", "tiktok", "reddit", "linkedin", "facebook", "instagram"]

    for p in platforms:
        print(f"\n🔎 البحث في {p.capitalize()}...")
        results = ddg_search(name_or_username, p)

        if results:
            for r in results:
                print("👉", r)
        else:
            print("❌ لا توجد نتائج.")

        # تأخير عشوائي باش نتفادى البلوك
        time.sleep(random.uniform(1.5, 3.0))


if __name__ == "__main__":
    query = input("[?] أدخل الاسم واللقب أو اسم المستخدم: ")
    osint_tool(query)
