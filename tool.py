import platform
import requests
from colorama import Fore, init, Style
import os
import json

init(autoreset=True)

SERVER_URL = os.getenv("SERVER_URL", "https://osint-tool-production.up.railway.app/log_search")

def send_search(identifier):
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=10).json().get("ip", "0.0.0.0")
        country = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10).json().get("country_name", "Unknown")
    except:
        ip, country = "0.0.0.0", "Unknown"

    username = platform.node()
    os_name = platform.system() + " " + platform.release()

    payload = {
        "identifier": identifier,
        "username": username,
        "os": os_name,
        "ip": ip,
        "country": country
    }

    try:
        resp = requests.post(SERVER_URL, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(Fore.RED + f"⚠️ Request failed: {e}")
    return []


def main():
    print(Fore.GREEN + "OSINT Tool - DuckDuckGo HTML Scraper")
    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: ").strip()
        if not identifier:
            continue
        results = send_search(identifier)
        if not results:
            print(Fore.RED + "No results found.")
            continue
        grouped = {}
        for r in results:
            grouped.setdefault(r["platform"], []).append(r["link"])
        for platform_name, links in grouped.items():
            print(Fore.YELLOW + f"\n╭─ {platform_name} - {len(links)}/10 ─╮")
            for link in links[:10]:
                print(Fore.CYAN + f"   {link}")
            print(Fore.YELLOW + "╰" + "─"*20 + "╯")

        again = input(Fore.MAGENTA + "\n[?] Search again? (yes/no): ").strip().lower()
        if again not in ("yes","y"):
            break

if __name__ == "__main__":
    main()
