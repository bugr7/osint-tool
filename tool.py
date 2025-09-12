# tool.py
import os
import time
import socket
import platform
import requests
from ddg3 import DDGS  # التعديل: استخدم DDGS بدل ddg
from datetime import datetime

ddgs = DDGS()  # إنشاء كائن DDGS

RAILWAY_URL = os.getenv("RAILWAY_SERVER_URL")  # مثال: http://127.0.0.1:5000/log_search

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

MAX_RESULTS = 10
RETRY_DELAY = 5  # ثواني عند DuckDuckGo 202

def log_to_server(username, user_ip, os_name, search_query):
    try:
        data = {
            "username": username,
            "ip": user_ip,
            "os": os_name,
            "search": search_query,
            "created_at": datetime.utcnow().isoformat()
        }
        requests.post(RAILWAY_URL, json=data, timeout=10)
    except Exception as e:
        print("⚠️ Could not log to server:", e)

def get_user_info():
    username = input("[?] Enter username or first/last name: ").strip()
    user_ip = requests.get("https://api.ipify.org").text
    os_name = platform.system() + " " + platform.release()
    return username, user_ip, os_name

def search_platform(query, platform_name, domain):
    search_query = f"{query} site:{domain}"
    attempts = 0
    while attempts < 5:
        try:
            results = ddgs.text(search_query)  # التعديل: استخدم text() بدل ddg()
            if results:
                # بعض النتائج ممكن تكون نصوص فقط، لذلك نبحث على الروابط إن وجدت
                links = [r for r in results if r.startswith("http")]
                return links[:MAX_RESULTS]
            else:
                attempts += 1
                time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            print(f"⚠️ DuckDuckGo request error ({platform_name}): {e}")
            attempts += 1
            time.sleep(RETRY_DELAY)
    return []

def main():
    username, user_ip, os_name = get_user_info()
    log_to_server(username, user_ip, os_name, username)

    for platform_name, domain in PLATFORMS.items():
        print(f"\n🔍 Searching {platform_name}...")
        try:
            links = search_platform(username, platform_name, domain)
            if links:
                print(f"✅ {platform_name}: {len(links)}/{MAX_RESULTS}")
                for link in links:
                    print(f"   {link}")
            else:
                print(f"❌ {platform_name}: No results found.")
        except Exception as e:
            print(f"⚠️ {platform_name} search failed:", e)

if __name__ == "__main__":
    main()
