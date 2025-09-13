#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from colorama import Fore, init

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
print(Fore.CYAN + "[*] أداة البحث DuckDuckGo OSINT\n")

# ===== دالة البحث =====
def search_ddg(query, max_results=5):
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.post(url, data=params, headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for a in soup.select(".result__a")[:max_results]:
        title = a.get_text()
        link = a.get("href")
        results.append({"title": title, "href": link})
    return results

# ===== البرنامج الرئيسي =====
def main():
    while True:
        query = input(Fore.YELLOW + "[?] أدخل كلمة البحث (أو اكتب exit للخروج): ").strip()
        if query.lower() == "exit":
            print(Fore.GREEN + "[+] تم الخروج من الأداة.")
            break

        print(Fore.CYAN + f"[+] جاري البحث عن: {query}")
        try:
            results = search_ddg(query, max_results=5)
            if not results:
                print(Fore.RED + "[!] لا توجد نتائج.")
            else:
                for idx, r in enumerate(results, 1):
                    print(Fore.GREEN + f"{idx}. {r['title']}")
                    print(Fore.CYAN + f"    {r['href']}")
        except Exception as e:
            print(Fore.RED + f"[!] حدث خطأ: {e}")

if __name__ == "__main__":
    main()
