import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style
import time
import platform

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
print(Fore.RED + "[*] أداة البحث OSINT مع تحسينات Session + بدائل للمنصات الصعبة" + Fore.GREEN + "\n")

# ====== منصات رئيسية ======
PLATFORMS = {
    "Facebook": "facebook.com",
    "Instagram": "instagram.com",
    "YouTube": "youtube.com",
    "TikTok": "tiktok.com",
    "Snapchat": "snapchat.com",
    "Reddit": "reddit.com",
    "Twitter": "twitter.com",
    "Pinterest": "pinterest.com",
    "LinkedIn": "linkedin.com",
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

# ====== دالة بدائل للمنصات الصعبة ======
def alternative_links(query, platform_name):
    # أمثلة بدائل بسيطة
    if platform_name == "Twitter":
        return search_ddg(query, site="nitter.net")
    if platform_name == "Reddit":
        return search_ddg(query, site="old.reddit.com")
    if platform_name == "LinkedIn":
        return search_ddg(query, site="linkedin.com")
    if platform_name == "Pinterest":
        return search_ddg(query, site="pinterest.com")
    return []

# ====== عرض النتائج ======
def run_checks(identifier):
    print(Fore.MAGENTA + "\n" + "="*60)
    print(Fore.MAGENTA + f"🔍 بدء البحث عن: {identifier}")
    print(Fore.MAGENTA + "="*60 + "\n")

    for platform_name, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"🔍 البحث في {platform_name}...")
        # البحث الأساسي
        links = search_ddg(identifier, site=domain, max_results=5)
        # إذا المنصة صعبة ولا نتائج → استخدم البدائل
        if not links and platform_name in ["Twitter", "Reddit", "LinkedIn", "Pinterest"]:
            links = alternative_links(identifier, platform_name)

        count = len(links)
        print(Fore.GREEN + f"✅ {platform_name}: {count}/5 نتائج")

        if links:
            for link in links:
                print(Fore.CYAN + f"   {link['title']} -> {link['href']}")
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
