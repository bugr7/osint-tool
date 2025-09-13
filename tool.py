import time
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

# ===== DuckDuckGo Search =====
def search_ddg(query, max_results=10):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(r.get("href"))
            time.sleep(0.2)  # Avoid 0/10 bug
    return results

# ===== Bing Search (simple scrape) =====
def search_bing(query, max_results=10):
    url = f"https://www.bing.com/search?q={query}&count={max_results}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    links = []
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("li.b_algo h2 a")[:max_results]:
            links.append(a["href"])
    return links

# ===== Qwant Search (simple scrape) =====
def search_qwant(query, max_results=10):
    url = f"https://www.qwant.com/?q={query}&t=web"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    links = []
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a.result-link")[:max_results]:
            links.append(a["href"])
    return links

# ===== Main =====
def main():
    print(r"""
 /$$$$$$$                                   /$$$$$$$$
| $$__  $$                                 |_____ $$/
| $$  \ $$ /$$   /$$  /$$$$$$         /$$$$$$   /$$/ 
| $$$$$$$/| $$  | $$ /$$__  $$ /$$$$$$|____  $$ /$$/  
| $$__  $$| $$  | $$| $$  \__/|______/ /$$$$$$$| $$   
| $$  \ $$| $$  | $$| $$       /$$    /$$__  $$| $$   
| $$  | $$|  $$$$$$/| $$      | $$   |  $$$$$$$| $$   
|__/  |__/ \______/ |__/      |__/    \_______/|__/   
    """)
    print("[*] OSINT Search Tool")

    while True:
        query = input("[?] Enter your search query (or type exit to quit): ").strip()
        if query.lower() == "exit":
            break

        print(f"\n[+] Searching for: {query}\n")

        sources = {
            "DuckDuckGo": search_ddg,
            "Bing": search_bing,
            "Qwant": search_qwant
        }

        for name, func in sources.items():
            try:
                results = func(query, 10)
                print(f"\n--- {name} ({len(results)}/10) ---")
                if results:
                    for i, link in enumerate(results, 1):
                        print(f"[{i}] {link}")
                else:
                    print("⚠️ No results")
            except Exception as e:
                print(f"❌ Error in {name}: {e}")
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()
