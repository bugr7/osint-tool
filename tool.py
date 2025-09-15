import requests
from bs4 import BeautifulSoup

def bing_search(query, platform, limit=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
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

    # نركز فقط على نتائج البحث الرئيسية
    for item in soup.find_all("li", {"class": "b_algo"}):
        a_tag = item.find("a", href=True)
        if a_tag:
            href = a_tag["href"]
            if href.startswith("http") and platform in href:
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
