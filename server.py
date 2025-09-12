# server.py
from flask import Flask, request, jsonify, Response
import sqlite3
import json
import time
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import traceback

app = Flask(__name__)

# ===== إعداد قاعدة البيانات =====
DATABASE_FILE = "osint.db"

def get_conn():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def migrate():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        platform TEXT,
        link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
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
    conn.commit()
    conn.close()

migrate()

# ===== منصات =====
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
MAX_RESULTS = 10

session = requests.Session()
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}
session.headers.update(HEADERS)

# ===== دالة تحويل Rows إلى dict =====
def row_to_dict(row):
    try:
        return {k: row[k] for k in row.keys()}
    except Exception:
        return str(row)

# ===== البحث في DuckDuckGo =====
def duckduckgo_search_links(query, site=None, num_results=MAX_RESULTS):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    links = []

    for attempt in range(5):
        try:
            resp = session.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                anchors = soup.select("a.result__a") or soup.find_all("a")
                for a in anchors:
                    href = a.get("href") or a.get("data-href") or a.get("data-redirect")
                    if href:
                        if "uddg=" in href:
                            m = re.search(r"uddg=([^&]+)", href)
                            if m:
                                href = urllib.parse.unquote(m.group(1))
                        if href.startswith("http") and href not in links:
                            links.append(href)
                    if len(links) >= num_results:
                        break
                # فالباك regex
                if len(links) < num_results:
                    found = re.findall(r'href="(https?://[^"]+)"', resp.text)
                    for f in found:
                        if f not in links and "duckduckgo.com" not in f:
                            links.append(f)
                        if len(links) >= num_results:
                            break
                return links[:num_results]
            elif resp.status_code in (429, 202):
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            else:
                break
        except Exception as e:
            print("⚠️ DuckDuckGo search error:", e)
            traceback.print_exc()
            time.sleep(1)
    return links

# ===== API =====
@app.route("/search", methods=["POST"])
def search():
    try:
        data = request.get_json(silent=True) or {}
        identifier = (data.get("identifier") or "").strip()
        if not identifier:
            return jsonify([])

        # تسجيل البحث
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
                ("server_user", "ServerOS", "Unknown", "0.0.0.0", identifier)
            )
            conn.commit()
        except Exception as e:
            print("DB insert error:", e)

        results = []

        for platform_name, domain in PLATFORMS.items():
            try:
                # البحث في DuckDuckGo
                links = duckduckgo_search_links(identifier, domain, num_results=MAX_RESULTS)
                for link in links:
                    results.append({"platform": platform_name, "link": link})
                    # حفظ في الكاش DB
                    try:
                        cur.execute(
                            "INSERT INTO results (query, platform, link) VALUES (?, ?, ?)",
                            (identifier, platform_name, link)
                        )
                        conn.commit()
                    except Exception as e:
                        print("Cache insert error:", e)
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"Unhandled error searching {platform_name}:", e)
                traceback.print_exc()
                continue

        conn.close()
        # تحويل النتائج إلى JSON آمن
        return Response(
            json.dumps(results, ensure_ascii=False),
            mimetype="application/json"
        )

    except Exception as e:
        print("❌ Fatal error in /search:", e)
        traceback.print_exc()
        return jsonify([])

@app.route("/")
def index():
    return "OSINT Tool API running..."

if __name__ == "__main__":
    # لا نغيّر بورت Railway (استخدم الافتراضي أو PORT environment variable)
    import os
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
