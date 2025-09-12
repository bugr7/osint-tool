# osint_tool_ddg.py

import platform
import time
from colorama import Fore, init, Style
from libsql_client import create_client_sync
from migrate import migrate
from duckduckgo_search import DDGS

init(autoreset=True)

# ===== إعداد Turso =====
DATABASE_URL = "https://search-osmoh.aws-eu-west-1.turso.io"  
AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NTc0MjkxNzEsImlkIjoiMGMwODllMjUtN2RiMC00Y2I1LWJhMDAtYWI1NTgxZjNjYjAxIiwicmlkIjoiYTM2YjJhZGQtNTU5NC00NDUxLThiY2EtZWRkNDgwZjI2ZWM0In0.4EdUBRRTA1uYTdGWnOP4jwnuFPZ6IrzuCBlzBdWtb31qw7B9vIX7rsiRZEUA6-Bf8hgcA-LaEkpPcl-r-csjCg"

client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
migrate(client)

# ===== دالة البحث =====
def search_ddg(query, max_results=10):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(r)
    return results

# ===== دالة الحفظ في قاعدة البيانات =====
def save_results(query, results):
    for r in results:
        try:
            client.execute(
                "INSERT INTO searches (query, title, link, snippet, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                [query, r.get("title"), r.get("href"), r.get("body"),],
            )
        except Exception as e:
            print(Fore.RED + f"[!] خطأ في الحفظ: {e}")

# ===== البرنامج الرئيسي =====
def main():
    print(Fore.GREEN + """
 /$$$$$$$                                   /$$$$$$$$
| $$__  $$                                 |_____ $$/
| $$  \ $$ /$$   /$$  /$$$$$$         /$$$$$$   /$$/ 
| $$$$$$$/| $$  | $$ /$$__  $$ /$$$$$$|____  $$ /$$/  
| $$__  $$| $$  | $$| $$  \__/|______/ /$$$$$$$| $$   
| $$  \ $$| $$  | $$| $$       /$$    /$$__  $$| $$   
| $$  | $$|  $$$$$$/| $$      | $$   |  $$$$$$$| $$   
|__/  |__/ \______/ |__/      |__/    \_______/|__/   
    """)
    print(Style.BRIGHT + Fore.CYAN + "[*] أداة البحث DuckDuckGo OSINT")

    while True:
        query = input(Fore.YELLOW + "\n[?] أدخل كلمة البحث (أو اكتب exit للخروج): ").strip()
        if query.lower() == "exit":
            print(Fore.CYAN + "[*] تم إنهاء البرنامج.")
            break

        print(Fore.CYAN + f"[+] جاري البحث عن: {query}")
        results = search_ddg(query, max_results=5)

        if not results:
            print(Fore.RED + "[!] لم يتم العثور على نتائج.")
            continue

        print(Fore.GREEN + f"[+] النتائج ({len(results)}):\n")
        for i, r in enumerate(results, start=1):
            print(Fore.MAGENTA + f"{i}. {r.get('title')}")
            print(Fore.WHITE + f"   الرابط: {r.get('href')}")
            print(Fore.LIGHTBLACK_EX + f"   الوصف: {r.get('body')}\n")

        save_results(query, results)
        print(Fore.CYAN + "[*] تم حفظ النتائج في قاعدة البيانات.")

        time.sleep(1)

if __name__ == "__main__":
    main()
