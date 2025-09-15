import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
]

def ddg_search(query, platform, limit=5, retries=3):
    url = f"https://html.duckduckgo.com/html/?q={query}+site:{platform}.com"

    for attempt in range(retries):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            for a in soup.select("a.result__a"):
                href = a.get("href")
                if href and "uddg=" in href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if "uddg" in parsed:
                        real_url = parsed["uddg"][0]
                        if platform in real_url:
                            results.append(real_url)
                if len(results) >= limit:
                    break
            return results

        elif response.status_code == 202:
            print(f"[!] DuckDuckGo حظر مؤقت (202) - محاولة {attempt+1}/{retries}...")
            time.sleep(random.uniform(3, 6))  # انتظر شوية وجرب ثاني
        else:
            print(f"[!] خطأ في DuckDuckGo: {response.status_code}")
            break

    return []


def osint_tool(name_or_username):
    platforms = {
    "youtube": ["youtube.com", "youtu.be"],
    "tiktok": ["tiktok.com"],
    "reddit": ["reddit.com"],
    "linkedin": ["linkedin.com"],
    "facebook": ["facebook.com", "fb.com"],
    "instagram": ["instagram.com"]
}

    for p in platforms:
        print(f"\n🔎 البحث في {p.capitalize()}...")
        results = ddg_search(name_or_username, p)
        if results:
            for r in results:
                print("👉", r)
        else:
            print("❌ لا توجد نتائج.")
        time.sleep(random.uniform(2, 4))  # تأخير بسيط بين كل منصة


if __name__ == "__main__":
    query = input("[?] أدخل الاسم واللقب أو اسم المستخدم: ")
    osint_tool(query)
