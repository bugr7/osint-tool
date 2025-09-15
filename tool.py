import requests
from bs4 import BeautifulSoup

# دالة للبحث في Bing
def bing_search(query, platform, limit=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/117.0 Safari/537.36"
    }
    url = f"https://www.bing.com/search?q={query}+site:{platform}.com"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"[!] خطأ في جلب النتائج من {platform}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        # نحول الروابط الداخلية إلى روابط كاملة
        if href.startswith("/"):
            href = "https://www.bing.com" + href

        if platform in href and href not in results:
            results.append(href)
        if len(results) >= limit:
            break

    return results


def osint_tool(name_or_username):
    platforms = ["youtube", "tiktok", "reddit", "linkedin"]

    for p in platforms:
        print(f"\n🔎 البحث في {p.capitalize()}...")
        results = bing_search(name_or_username, p)
        if results:
            for r in results:
                print("👉", r)
        else:
            print("❌ لا توجد نتائج.")


if __name__ == "__main__":
    query = input("[?] أدخل الاسم واللقب أو اسم المستخدم: ")
    osint_tool(query)
