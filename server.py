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
from urllib.parse import urlparse, unquote

app = Flask(__name__)

# ===== إعداد Turso =====
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = None
if DATABASE_URL and AUTH_TOKEN:
    try:
        client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
        migrate(client)
    except Exception as e:
        print("⚠️ Turso init failed:", e)
else:
    print("⚠️ DATABASE_URL or AUTH_TOKEN not set — DB disabled (set them in Railway env).")

# إنشاء الجداول إذا أمكن
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

# إعدادات الشبكة
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 1.0))  # أقل قليلاً لأن الآن نطلب مرة واحدة
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


def duckduckgo_search_all(query, max_links=200):
    """
    نفّذ طلب واحد إلى DuckDuckGo HTML endpoint، واخرج قائمة روابط منظمة.
    نستخدم retries بسيط (exponential backoff) لحالات 429/202.
    """
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    links = []
    seen = set()

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=20)
            print(f"🔎 DuckDuckGo query: '{query[:60]}' | status={resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                anchors = soup.select("a.result__a")
                if not anchors:
                    anchors = soup.find_all("a")

                for a in anchors:
                    href = a.get("href") or ""
                    link = None
                    if "uddg=" in href:
                        m = re.search(r'uddg=([^&]+)', href)
                        if m:
                            try:
                                link = unquote(m.group(1))
                            except Exception:
                                link = None
                    else:
                        # بعض الأحيان href هو مسار كامل أو رابط مباشر
                        if href.startswith("/l/") or href.startswith("/r/"):
                            # حاول استخراج uddg داخل href
                            m = re.search(r'uddg=([^&]+)', href)
                            if m:
                                try:
                                    link = unquote(m.group(1))
                                except Exception:
                                    link = None
                        elif href.startswith("http"):
                            link = href

                    # fallback: بعض الروابط مدفونة داخل attributes أخرى
                    if not link:
                        data_href = a.get("data-href") or a.get("data-redirect")
                        if data_href:
                            link = data_href

                    if link:
                        # تأكد من عدم احتواء رابط DuckDuckGo نفسه
                        if "duckduckgo.com" in link:
                            continue
                        # normalize
                        link = link.strip()
                        if link not in seen:
                            seen.add(link)
                            links.append(link)
                        if len(links) >= max_links:
                            break

                # فالباك بسيط عبر regex لو لم نعثر على شيء كافٍ
                if not links:
                    found = re.findall(r'href="(https?://[^"]+)"', resp.text)
                    for link in found:
                        if 'duckduckgo.com' not in link and link not in seen:
                            seen.add(link)
                            links.append(link)
                        if len(links) >= max_links:
                            break

                return links

            elif resp.status_code in (429, 202):
                wait = 2 ** attempt
                print(f"⏳ DuckDuckGo returned {resp.status_code}, retrying after {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue
            else:
                print("❌ DuckDuckGo returned status:", resp.status_code)
                break

        except Exception as e:
            print("⚠️ Error fetching DuckDuckGo:", e)
            traceback.print_exc()
            time.sleep(1)

    return links


@app.route("/search", methods=["POST"])
def search():
    try:
        data = request.get_json(silent=True) or {}
        identifier = (data.get("identifier", "") or "").strip()
        print(f"🔍 Searching for: {identifier}", flush=True)
        if not identifier:
            return jsonify([])

        # تخزين البحث (محاولة آمنة - لا نكسر في حال فشل DB)
        if client:
            try:
                client.execute(
                    "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
                    ("server_user", "ServerOS", "Unknown", "0.0.0.0", identifier)
                )
            except Exception as e:
                print("DB insert error:", e)

        results = []

        # أولاً: هل هناك كاش كامل للـ query؟ نقرأه مرة واحدة
        cached_rows = []
        if client:
            try:
                res = client.execute("SELECT platform, link FROM search_cache WHERE query=?", (identifier,))
                try:
                    cached_rows = res.fetchall()
                except Exception:
                    # إذا لم يكن res كائن DB مثل fetchall، نحاول تحويله لقائمة
                    try:
                        cached_rows = list(res)
                    except Exception:
                        cached_rows = []
            except Exception as e:
                print("Cache select error:", e)
                cached_rows = []

        if cached_rows:
            for row in cached_rows:
                # row يمكن أن يكون tuple أو قيمة مفردة
                if isinstance(row, (list, tuple)) and len(row) >= 2:
                    platform_name, link = row[0], row[1]
                else:
                    # حاول التعامل مع شكل غير متوقع
                    continue
                results.append({"platform": platform_name, "link": link})
            print(f"Found {len(results)} results from cache", flush=True)
            return jsonify(results)

        # لا كاش: نجلب نتائج DuckDuckGo مرة واحدة ونصنّفها حسب الدومين
        all_links = duckduckgo_search_all(identifier, max_links=300)
        print(f"🔎 Total raw links fetched: {len(all_links)}", flush=True)

        # صنّف حسب المنصات
        for platform_name, domain in PLATFORMS.items():
            count = 0
            for link in all_links:
                try:
                    netloc = urlparse(link).netloc.lower()
                except Exception:
                    netloc = ""
                if domain in netloc or domain in link.lower():
                    results.append({"platform": platform_name, "link": link})
                    count += 1
                    # خزّن في الكاش لو ممكن
                    if client:
                        try:
                            client.execute(
                                "INSERT INTO search_cache (query, platform, link) VALUES (?, ?, ?)",
                                (identifier, platform_name, link)
                            )
                        except Exception as e:
                            print("Cache insert error:", e)
                if count >= 10:
                    break
            # small delay between platform classification (لاجتماع UX وضمن الموارد)
            time.sleep(REQUEST_DELAY)

        print(f"Found {len(results)} results total", flush=True)
        return jsonify(results)

    except Exception as e:
        print("❌ Fatal error in /search:", e)
        traceback.print_exc()
        # بدل 500 نعيد 200 مع لستة فارغة ليتعامل الكلاينت بأمان
        return jsonify([])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
