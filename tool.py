import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style
import platform
import time

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

REQUEST_DELAY = 1.5  # ثانية ونصف بين كل بحث
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0 Safari/537.36"
}

# ===== البحث في Qwant =====
def search_qwant(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = f"https://www.qwant.com/?l=en&q={requests.utils.quote(search_query)}&t=web"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if "captcha" in resp.text.lower() or "protection" in resp.text.lower():
            print(Fore.RED + "⚠️ Qwant CAPTCHA/Protection detected.")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.select("a.result-link"):
            href = a.get("href")
            if href and href.startswith("http"):
                links.append(href)
            if len(links) >= num_results:
                break
        return links
    except Exception as e:
        print(Fore.RED + f"⚠️ Error fetching from Qwant: {e}")
        return []

# ===== عرض النتائج =====
def run_checks(identifier):
    print(Fore.MAGENTA + "\n" + "="*60)
    print(Fore.MAGENTA + f"🔍 Start search about: {identifier}")
    print(Fore.MAGENTA + "="*60 + "\n")

    for platform_name, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"🔍 Searching {platform_name}...")
        links = search_qwant(identifier, domain)
        count = len(links)

        if count > 0:
            print(Fore.GREEN + f"✅ {platform_name}: {count} results")
            for link in links:
                print(Fore.CYAN + f"   {link}")
        else:
            print(Fore.RED + f"⚠️ No results from Qwant for {platform_name}")

        print(Fore.MAGENTA + "-"*60 + "\n")
        time.sleep(REQUEST_DELAY)

# ===== البرنامج الرئيسي =====
def main():
    print(Fore.GREEN + """
 /$$$$$$$                                   /$$$$$$$$
| $$__  $$                                 |_____ $$/
| $$  \ $$ /$$   /$$  /$$$$$$         /$$$$$$   /$$/
| $$$$$$$ | $$  | $$ /$$__  $$       /$$__  $$ /$$/
| $$__  $$| $$  | $$| $$  \ $$      | $$  \__//$$/
| $$  \ $$| $$  | $$| $$  | $$      | $$     /$$/
| $$$$$$$/|  $$$$$$/|  $$$$$$$      | $$    /$$/
|_______/  \______/  \____  $$      |__/   |__/
                     /$$  \ $$
                    |  $$$$$$/
                     \______/
""" + Fore.RED + "OSINT Tool - Qwant Version" + Fore.GREEN + "\n")

    print(Fore.WHITE + "🔎 Platforms covered: Facebook, Instagram, Youtube, TikTok, Snapchat, Reddit, Twitter, Pinterest, LinkedIn\n")

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        run_checks(identifier)

        again = input(Fore.MAGENTA + "\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "\n[✔] Exiting OSINT tool. Bye 👋")
            break

if __name__ == "__main__":
    main()
