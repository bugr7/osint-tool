# server.py
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

DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = None
try:
    client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
    migrate(client)
except Exception as e:
    print("⚠️ Turso init failed:", e)


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

    try:
        client.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            platform TEXT,
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    except Exception as e:
        print("Error creating search_cache:", e)


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


REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 1.5))  # تأخير افتراضي
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 2))


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
    """البحث في DuckDuckGo وإرجاع روابط نظيفة"""
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}

    links = []

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=20)
            print(f"🔎 Searching: {search_query} | Status: {resp.status_code}")

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                anchors = soup.select("a.result__a")
                if not anchors:
                    anchors = soup.find_all("a")

                for a in anchors:
                    link = None
                    href = a.get("href")
                    if href:
                        if "uddg=" in href:
                            m = re.search(r"uddg=([^&]+)", href)
                            if m:
                                try:
                                    link = urllib.parse.unquote(m.group(1))
                                except Exception:
                                    link = None
                        else:
                            link = href

                    if not link:
                        data_href = a.get("data-href") or a.get("data-redirect")
                        if data_href:
                            link = data_href

                    if link and link.startswith("http"):
                        if "duckduckgo.com" not in link and link not in links:
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

            elif resp.status_code in (429, 202):
                wait = 2 ** attempt
                print(f"⏳ Got {resp.status_code}, retrying after {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue
            else:
                print("❌ DuckDuckGo returned status:", resp.status_code)
                break

        except Exception as e:
            print("⚠️ Error searching:", e)
            traceback.print_exc()
            time.sleep(1)

    return links


@app.route("/search", methods=["POST"])
def search():
    try:
        data = request.get_json(silent=True) or {}
        identifier = (data.get("identifier", "") or "").strip()
        if not identifier:
            return jsonify([])

        print(f"🔍 Searching for: {identifier}", flush=True)

        
        if client:
            try:
                client.execute(
                    "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
                    ("server_user", "ServerOS", "Unknown", "0.0.0.0", identifier)
                )
            except Exception as e:
                print("DB insert error:", e)

        results = []

        for platform_name, domain in PLATFORMS.items():
            try:
                
                cached = []
                if client:
                    try:
                        res = client.execute(
                            "SELECT link FROM search_cache WHERE query=? AND platform=?",
                            (identifier, platform_name)
                        )
                        if hasattr(res, "fetchall"):
                            cached = res.fetchall()
                        else:
                            cached = list(res)
                    except Exception as e:
                        print("Cache select error:", e)
                        cached = []

                if cached:
                    for row in cached:
                        link = row[0] if isinstance(row, (list, tuple)) else row
                        results.append({"platform": platform_name, "link": link})
                    continue

                
                links = duckduckgo_search_links(identifier, domain, num_results=10)
                for link in links:
                    results.append({"platform": platform_name, "link": link})
                    if client:
                        try:
                            client.execute(
                                "INSERT INTO search_cache (query, platform, link) VALUES (?, ?, ?)",
                                (identifier, platform_name, link)
                            )
                        except Exception as e:
                            print("Cache insert error:", e)
                time.sleep(REQUEST_DELAY)

            except Exception as e:
                print(f"Unhandled error searching {platform_name}:", e)
                traceback.print_exc()
                continue

        print(f"✅ Found {len(results)} results for '{identifier}'", flush=True)
        return jsonify(results)

    except Exception as e:
        print("❌ Fatal error in /search:", e)
        traceback.print_exc()
        return jsonify([])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

