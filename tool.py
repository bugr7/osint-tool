import requests
from bs4 import BeautifulSoup
import time, random

# ===== DuckDuckGo Search =====
def ddg_search(query, platform, limit=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/117.0 Safari/537.36"
    }
    url = f"https://lite.duckduckgo.com/lite/?q={query}+site:{platform}.com"

    response = requests.get(url, headers=headers, timeout=10)
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


# ===== Bing Search =====
def bing_search(query, platform, limit=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/117.0 Safari/537.36"
    }
    url = f"https://www.bing.com/search?q={query}+site:{platform}.com"

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"[!] خطأ في Bing: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for h2 in soup.find_all("h2"):
        a = h2.find("a", href=True)
        if a and platform in a["href"]:
            results.append(a["href"])
        if len(results) >= limit:
            break

    return results


# ===== Main OSINT Tool =====
def osint_tool(name_or_username):
    platforms = {
        "youtube": "ddg",
        "tiktok": "ddg",
        "reddit": "bing",
        "linkedin": "bing"
    }

    for p, engine in platforms.items():
        print(f"\n🔎 البحث في {p.capitalize()}...")

        if engine == "ddg":
            results = ddg_search(name_or_username, p)
        else:
            results = bing_search(name_or_username, p)

        if results:
            for r in results:
                print("👉", r)
        else:
            print("❌ لا توجد نتائج.")

        # تأخير عشوائي لتفادي الحظر
        time.sleep(random.uniform(1.5, 3.5))


if __name__ == "__main__":
    query = input("[?] أدخل الاسم واللقب أو اسم المستخدم: ")
    osint_tool(query)
