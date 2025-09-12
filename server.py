# server.py
from flask import Flask, request, jsonify
from libsql_client import create_client_sync
from ddgs import DDGS
import os
import time

app = Flask(__name__)

# ===== إعداد Turso DB =====
DATABASE_URL = os.getenv("DATABASE_URL", "https://search-osmoh.aws-eu-west-1.turso.io")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)

# ===== إنشاء جدول إذا لم يكن موجود =====
client.execute("""
CREATE TABLE IF NOT EXISTS users_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    platform TEXT,
    link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ===== منصات رئيسية =====
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

ddgs = DDGS()

# ===== دالة البحث =====
def duckduckgo_search(identifier, site=None, max_results=15):
    query = f"{identifier} site:{site}" if site else identifier
    results = []
    attempts = 0
    backoff = 1
    while attempts < 5:
        try:
            ddg_results = ddgs.text(query, max_results=max_results)
            for r in ddg_results:
                if "href" in r and r["href"]:
                    results.append(r["href"])
            if results:
                return results
            else:
                attempts += 1
                time.sleep(backoff)
                backoff *= 2
        except Exception as e:
            attempts += 1
            time.sleep(backoff)
            backoff *= 2
    return results

@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    identifier = data.get("identifier")
    if not identifier:
        return jsonify({"error": "No identifier provided"}), 400

    final_results = []
    for platform_name, domain in PLATFORMS.items():
        links = duckduckgo_search(identifier, domain, max_results=10)
        # تخزين في Turso
        for link in links:
            client.execute(
                "INSERT INTO users_log (username, platform, link) VALUES (?, ?, ?)",
                (identifier, platform_name, link)
            )
            final_results.append({
                "platform": platform_name,
                "link": link
            })

    return jsonify(final_results), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
