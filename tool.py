import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style
import platform
import time

# تفعيل الألوان
init(autoreset=True)

# ===== المنصات =====
PLATFORMS = {
    "Facebook": "facebook.com",
    "Instagram": "instagram.com",
    "Youtube": "youtube.com",
    "TikTok": "tiktok.com",
    "Snapchat": "snapchat.com",
    "Reddit": "reddit.com",
    "Twitter": "twitter.com",
    "Pinterest": "pinterest.com",
    "LinkedIn": "linkedin.com",
}

REQUEST_DELAY = 0.5  # تأخير بين المنصات باش ما يبانش spam

# ===== دالة البحث في Bing =====
def search_bing(query, domain):
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}+site:{domain}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for item in soup.select("li.b_algo h2 a"):
        link = item.get("href")
        if link and domain in link:
            results.append(link)

    return results


# ===== تشغيل الفحص =====
def run_checks(identifier):
    for platform, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"\n🔍 Searching {platform}...")
        results = search_bing(identifier, domain)

        if not results:
            print(Fore.RED + f"⚠️ No results from Bing for {platform}")
        else:
            print(Fore.GREEN + f"✅ {platform}: {len(results)}/10")
            for link in results[:10]:
                print(Fore.CYAN + "   " + link)

        time.sleep(REQUEST_DELAY)


# ===== الدالة الرئيسية =====
def main():
    print(Fore.GREEN + """
 /$$$$$$$                                   /$$$$$$$$
| $$__  $$                                 |_____ $$/
| $$  \ $$ /$$   /$$  /$$$$$$         /$$$$$$   /$$/ 
| $$$$$$$ | $$  | $$ /$$__  $$       |____  $$ /$$/  
| $$__  $$| $$  | $$| $$$$$$$$        /$$$$$$$| $$   
| $$  \ $$| $$  | $$| $$_____/       /$$__  $$| $$   
| $$$$$$$/|  $$$$$$$|  $$$$$$$      |  $$$$$$$| $$   
|_______/  \____  $$ \_______/       \_______/|__/   
           /$$  | $$                                
          |  $$$$$$/                                
           \______/                                 
    """)
    print(Fore.CYAN + "===== أداة OSINT (Bing Only) =====\n")

    identifier = input(Fore.YELLOW + "[?] Enter username or first/last name: ").strip()
    if identifier:
        run_checks(identifier)
    else:
        print(Fore.RED + "⚠️ No input provided")


if __name__ == "__main__":
    main()
