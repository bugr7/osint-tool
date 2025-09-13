import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style
import time
import platform
import json

# ====== إعداد اللون ======
init(autoreset=True)

# ====== شعار الأداة ======
banner = r"""
 /$$$$$$$                                   /$$$$$$$$
| $$__  $$                                 |_____ $$/
| $$  \ $$ /$$   /$$  /$$$$$$         /$$$$$$   /$$/
| $$$$$$$/| $$  | $$ /$$__  $$ /$$$$$$|____  $$ /$$/
| $$__  $$| $$  | $$| $$  \__/|______/ /$$$$$$$| $$
| $$  \ $$| $$  | $$| $$       /$$    /$$__  $$| $$
| $$  | $$|  $$$$$$/| $$      | $$   |  $$$$$$$| $$
|__/  |__/ \______/ |__/      |__/    \_______/|__/
"""
print(Fore.GREEN + banner)
print(Fore.RED + "[*] أداة البحث OSINT مع تحسينات منصات متعددة" + Fore.GREEN + "\n")

# ====== منصات رئيسية ======
PLATFORMS = {
    "Facebook": "facebook.com",
    "Instagram": "instagram.com",
    "YouTube": "youtube.com",
    "TikTok": "tiktok.com",
    "Twitter": "twitter.com",
    "Reddit": "reddit.com",
    "LinkedIn": "linkedin.com",
    "Pinterest": "pinterest.com",
    "Snapchat": "snapchat.com",
}

REQUEST_DELAY = 2.0  # ثانية بين كل طلب لمنع الحجب

# ====== إنشاء Session ثابت ======
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

# ====== دالة البحث عبر DuckDuckGo HTML ======
def search_ddg(query, site=None, max_results=5):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    data = {"q": search_query}
    results = []

    try:
        response = session.post(url, headers=session.headers, data=data, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.select(".result__a")[:max_results]
        for a in links:
            title = a.get_text()
            href = a.get("href")
            results.append({"title": title, "href": href})
    except Exception as e:
        print(Fore.RED + f"[!] خطأ أثناء البحث: {e}")
    return results

# ====== بدائل للمنصات الصعبة ======
def alternative_search(query, platform_name, max_results=5):
    results = []
    try:
        if platform_name == "Twitter":
            # Nitter search
            nitter_url = f"https://nitter.net/search?f=tweets&q={requests.utils.quote(query)}"
            resp = session.get(nitter_url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            tweets = soup.select(".timeline-item .tweet-content")[:max_results]
            for t in tweets:
                text = t.get_text().strip()
                link_tag = t.find("a", href=True)
                link = "https://nitter.net" + link_tag["href"] if link_tag else ""
                results.append({"title": text, "href": link})

        elif platform_name == "Reddit":
            # old.reddit.com search JSON
            reddit_url = f"https://old.reddit.com/search.json?q={requests.utils.quote(query)}&sort=relevance"
            resp = session.get(reddit_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            data = resp.json()
            for item in data.get("data", {}).get("children", [])[:max_results]:
                post = item["data"]
                results.append({"title": post.get("title"), "href": "https://reddit.com" + post.get("permalink")})
        # LinkedIn, Pinterest, Snapchat → غير مدعوم
        elif platform_name in ["LinkedIn", "Pinterest", "Snapchat"]:
            results.append({"title": "[!] البحث لهذه المنصة يحتاج API أو Selenium", "href": ""})

    except Exception as e:
        print(Fore.RED + f"[!] خطأ أثناء البحث في {platform_name}: {e}")

    return results

# ====== عرض النتائج ======
def run_checks(identifier):
    print(Fore.MAGENTA + "\n" + "="*60)
    print(Fore.MAGENTA + f"🔍 بدء البحث عن: {identifier}")
    print(Fore.MAGENTA + "="*60 + "\n")

    for platform_name, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"🔍 البحث في {platform_name}...")
        # DuckDuckGo HTML للمواقع المدعومة
        if platform_name in ["Facebook", "Instagram", "YouTube", "TikTok"]:
            links = search_ddg(identifier, site=domain, max_results=5)
        else:
            # البدائل أو التحذيرات
            links = alternative_search(identifier, platform_name, max_results=5)

        count = len(links)
        print(Fore.GREEN + f"✅ {platform_name}: {count}/5 نتائج")

        if links:
            for link in links:
                title = link['title']
                href = link['href']
                if href:
                    print(Fore.CYAN + f"   {title} -> {href}")
                else:
                    print(Fore.CYAN + f"   {title}")
        else:
            print(Fore.RED + "   لا توجد نتائج.")

        print(Fore.MAGENTA + "-"*60 + "\n")
        time.sleep(REQUEST_DELAY)

# ====== البرنامج الرئيسي ======
def main():
    username = platform.node()
    os_name = platform.system() + " " + platform.release()

    while True:
        identifier = input(Fore.CYAN + "[?] أدخل كلمة البحث (أو اكتب exit للخروج): " + Style.RESET_ALL).strip()
        if identifier.lower() == "exit":
            print(Fore.GREEN + "\n[✔] تم الخروج من الأداة. إلى اللقاء 👋")
            break
        if not identifier:
            print(Fore.RED + "[!] لم يتم إدخال أي كلمة للبحث.")
            continue

        run_checks(identifier)

if __name__ == "__main__":
    main()
