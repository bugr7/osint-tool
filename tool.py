import cloudscraper
from bs4 import BeautifulSoup
import time

# إنشاء scraper
scraper = cloudscraper.create_scraper(browser={
    'browser': 'chrome',
    'platform': 'windows',
    'mobile': False
})

# محركات البحث
def search_bing(query):
    url = f"https://www.bing.com/search?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    res = scraper.get(url, headers=headers)
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        links = [a["href"] for a in soup.select("li.b_algo h2 a") if a.get("href")]
        return links
    return []

def search_ddg(query):
    url = f"https://duckduckgo.com/html/?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    res = scraper.get(url, headers=headers)
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        links = [a["href"] for a in soup.select(".result__a") if a.get("href")]
        return links
    return []

# دالة البحث مع fallback
def search(query, platform):
    print(f"\n🔎 البحث في {platform}...")
    q = f"{query} site:{platform}.com"
    results = search_bing(q)

    # fallback إذا ماكانش نتائج
    if not results:
        time.sleep(2)  # تهدئة
        results = search_ddg(q)

    if results:
        for link in results:
            print("✅", link)
        return results
    else:
        print("❌ لا توجد نتائج.")
        return []

if __name__ == "__main__":
    name = input("[?] أدخل الاسم واللقب أو اسم المستخدم: ")
    platforms = ["youtube", "tiktok", "reddit", "linkedin", "facebook", "instagram"]

    all_results = []
    for p in platforms:
        links = search(name, p)
        all_results.extend(links)
        time.sleep(2)

    # حفظ النتائج
    with open("results.txt", "w", encoding="utf-8") as f:
        for link in all_results:
            f.write(link + "\n")

    print("\n✅ النتائج تحفظت في results.txt")
