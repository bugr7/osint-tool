#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style

# ===== تهيئة الألوان =====
init(autoreset=True)

# ===== شعار الأداة =====
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
print(banner)
print(Fore.CYAN + "[*] أداة البحث DuckDuckGo OSINT - روابط المنصات\n")

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

# ===== دالة البحث عبر DuckDuckGo HTML =====
def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.post(url, data=params, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for a in soup.select(".result__a")[:num_results]:
            title = a.get_text()
            link = a.get("href")
            results.append({"title": title, "href": link})
        return results
    except Exception as e:
        print(Fore.RED + f"[!] خطأ أثناء البحث: {e}")
        return []

# ===== تشغيل البحث على كل المنصات =====
def run_checks(identifier):
    print(Fore.MAGENTA + "\n" + "="*60)
    print(Fore.MAGENTA + f"🔍 بدء البحث عن: {identifier}")
    print(Fore.MAGENTA + "="*60 + "\n")

    for platform_name, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"🔍 البحث في {platform_name}...")
        links = duckduckgo_search_links(identifier, domain, num_results=10)
        count = len(links)
        print(Fore.GREEN + f"✅ {platform_name}: {count}/10")

        if links:
            for idx, link in enumerate(links, 1):
                print(Fore.CYAN + f"   {idx}. {link['title']}")
                print(Fore.WHITE + f"      {link['href']}")
        else:
            print(Fore.RED + "   لا توجد نتائج.")

        print(Fore.MAGENTA + "-"*60 + "\n")

# ===== البرنامج الرئيسي =====
def main():
    while True:
        identifier = input(Fore.CYAN + "[?] أدخل اسم المستخدم أو الاسم الكامل (exit للخروج): " + Style.RESET_ALL).strip()
        if identifier.lower() == "exit":
            print(Fore.GREEN + "[✔] الخروج من الأداة. 👋")
            break

        run_checks(identifier)

if __name__ == "__main__":
    main()
