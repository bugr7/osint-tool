from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from migrate import migrate
import os
import time
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# ===== إعداد Turso =====
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
migrate(client)

# إنشاء جدول إذا ماكانش
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

REQUEST_DELAY = 0.3


def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}

    links = []
    try:
        resp = requests.post(url, data=params, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a.result__a"):
                link = a.get("href")
                if link and link.startswith("http"):
                    links.append(link)
                if len(links) >= num_results:
                    break
    except Exception as e:
        print(f"⚠️ Error searching {site}: {e}")

    return links


@app.route("/search", methods=["POST"])
def search():
    data = request.json
    identifier = data.get("identifier", "")
    if not identifier:
        return jsonify([])

    # تخزين البحث
    client.execute(
        "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
        ("server_user", "ServerOS", "Unknown", "0.0.0.0", identifier)
    )

    results = []
    for platform_name, domain in PLATFORMS.items():
        links = duckduckgo_search_links(identifier, domain)
        for link in links:
            results.append({"platform": platform_name, "link": link})
        time.sleep(REQUEST_DELAY)

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
