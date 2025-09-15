import requests
from bs4 import BeautifulSoup

def search_bing(query, site, max_results=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://www.bing.com/search?q={query}+site:{site}.com"
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    # جرّب الهيكل الأول (Bing إنجليزي)
    links = [a["href"] for a in soup.select("li.b_algo h2 a") if a.has_attr("href")]

    # إذا ما لقاهمش جرّب الهيكل الثاني (Bing عربي)
    if not links:
        links = [a["href"] for a in soup.select("h2 a") if a.has_attr("href")]

    return links[:max_results]

if __name__ == "__main__":
    query = "elon musk"
    for site in ["youtube", "tiktok", "reddit", "linkedin", "facebook", "instagram"]:
        print(f"\n🔎 البحث في {site.capitalize()}...")
        results = search_bing(query, site)
        if results:
            for link in results:
                print("👉", link)
        else:
            print("❌ لا توجد نتائج.")
