from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os
import time
import requests
from bs4 import BeautifulSoup
import traceback
import re
import urllib.parse

app = Flask(__name__)

# ===== إعداد Turso عبر Railway Variables =====
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = None
try:
    client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
    migrate(client)
except Exception as e:
    print("⚠️ Turso init failed:", e)

# إنشاء الجداول
if client:
    try:
        client.execute("""
        CREATE TABLE IF NOT EXISTS users_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            os TEXT,
            country TEXT,
            ip TEXT,
            search TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    except Exception as e:
        print("Error creating users_log:", e)

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

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 1.5))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 2))

# جلسة requests مع Header ثابت
session = requests.Session()
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
session.headers.update(HEADERS)


def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    links = []

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                anchors = soup.select("a.result__a") or soup.find_all("a")
                for a in anchors:
                    link = None
                    href = a.get("href")
                    if href:
                        if "uddg=" in href:
                            m = re.search(r"uddg=([^&]+)", href)
                            if m:
                                link = urllib.parse.unquote(m.group(1))
                        else:
                            link = href
                    if not link:
                        data_href = a.get("data-href") or a.get("data-redirect")
                        if data_href:
                            link = data_href
                    if link and link.startswith("http") and "duckduckgo.com" not in link and link not in links:
                        links.append(link)
                    if len(links) >= num_results:
                        break

                if not links:
                    found = re.findall(r'href="(https?://[^"]+)"', resp.text)
                    for link in found:
                        if "duckduckgo.com" not in link and link not in links:
                            links.append(link)
                        if len(links) >= num_results:
                            break

                return links
            else:
                time.sleep(2 ** attempt)
        except Exception as e:
            print("⚠️ Error searching:", e)
            traceback.print_exc()
            time.sleep(1)
    return links


@app.route("/log_search", methods=["POST"])
def log_search():
    data = request.get_json(silent=True) or {}
    identifier = data.get("identifier", "").strip()
    username = data.get("username", "unknown")
    os_name = data.get("os", "unknown")
    ip = data.get("ip", "0.0.0.0")
    country = data.get("country", "Unknown")

    if client:
        try:
            client.execute(
                "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
                (username, os_name, country, ip, identifier)
            )
        except Exception as e:
            print("DB insert error:", e)

    results = []
    for platform_name, domain in PLATFORMS.items():
        links = duckduckgo_search_links(identifier, domain, num_results=10)
        for link in links:
            results.append({"platform": platform_name, "link": link})
        time.sleep(REQUEST_DELAY)

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
