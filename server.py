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
import random

app = Flask(__name__)

# ===== إعداد Turso (من المتغيرات البيئية) =====
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

client = None
try:
    if DATABASE_URL and AUTH_TOKEN:
        client = create_client_sync(url=DATABASE_URL, auth_token=AUTH_TOKEN)
        migrate(client)
    else:
        print("⚠️ DATABASE_URL or AUTH_TOKEN not set. DB disabled.")
except Exception as e:
    print("⚠️ Turso init failed:", e)

# إنشـاء الجداول لو أمكن
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

# إعدادات الشبكة / السلوك
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 1.2))  # تأخير افتراضي لتقليل الحظر
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 2))
DESIRED_PER_PLATFORM = int(os.getenv("DESIRED_PER_PLATFORM", 10))

# جلسة requests مع Header ثابت
session = requests.Session()
HEADERS_POOL = [
    # مجموعة User-Agents (يمكن إضافة المزيد)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
]
session.headers.update({"User-Agent": random.choice(HEADERS_POOL)})


def generate_permutations(name):
    """
    توليد صيغ متعددة من الاسم لزيادة الاحتمالات:
    - الاسم كما هو
    - بدون مسافات
    - بنقطة/شرطة/underscore
    - firstlast و lastfirst
    - إضافة احتمالات مع حذف أحرف متوسطة
    """
    name = name.strip()
    parts = [p for p in name.split() if p]
    perms = []
    # الأصلية
    perms.append(name)
    # بدون مسافات
    perms.append("".join(parts))
    # نقط و underscores و شرطات
    if len(parts) >= 2:
        perms.append(".".join(parts))
        perms.append("_".join(parts))
        perms.append("-".join(parts))
        perms.append(parts[0] + parts[-1])
        perms.append(parts[-1] + parts[0])
    # كل جزء لوحده
    for p in parts:
        perms.append(p)
    # إضافات: lowercase
    perms = list(dict.fromkeys([p.lower() for p in perms if p]))  # إزالة المكررات والمحافظة على الترتيب
    return perms


def extract_links_from_html(resp_text, max_results):
    links = []
    # باك أب عبر regex
    found = re.findall(r'href=["\'](https?://[^"\' >]+)', resp_text)
    for l in found:
        if 'duckduckgo.com' not in l and l not in links:
            links.append(l)
        if len(links) >= max_results:
            break
    return links


def duckduckgo_search_links(query, site=None, num_results=10):
    """
    بحث ذكي: نحاول عدة permutations من query حتى نملأ num_results إن أمكن.
    نستخدم DuckDuckGo HTML endpoint ونفك روابط uddg إذا لزم.
    """
    base_query = f"{query} site:{site}" if site else query
    collected = []
    tried_queries = set()
    # اجمع permutations لتجربة متتابعة
    name_perms = generate_permutations(query)
    # أضف الاستعلام الكامل في البداية
    candidate_queries = [base_query] + [f"{p} site:{site}" if site else p for p in name_perms]

    # حد أقصى للـ attempts
    for candidate in candidate_queries:
        if len(collected) >= num_results:
            break
        if candidate in tried_queries:
            continue
        tried_queries.add(candidate)

        # تغيير user-agent عشوائياً من المجموعة
        session.headers.update({"User-Agent": random.choice(HEADERS_POOL)})

        url = "https://html.duckduckgo.com/html/"
        params = {"q": candidate}

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = session.get(url, params=params, timeout=20)
                print(f"🔎 DuckDuckGo search '{candidate[:80]}' | status={resp.status_code}", flush=True)

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    anchors = soup.select("a.result__a")
                    if not anchors:
                        anchors = soup.find_all("a")

                    for a in anchors:
                        link = None
                        href = a.get("href")
                        if href:
                            # فك udgg param
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
                            if "duckduckgo.com" not in link and link not in collected:
                                # simple filter: يجب أن يحتوي على الـ domain إذا كان مطبوعاً في الاستعلام (site:)
                                if site and site not in link:
                                    # إذا البحث كان site:domain، تجاهل الروابط التي لا تملك الدومين
                                    continue
                                collected.append(link)
                                print(f"   + found: {link}", flush=True)
                        if len(collected) >= num_results:
                            break

                    # لو لم نحصل على شيء كافٍ: استخدم regex باك أب
                    if len(collected) < num_results:
                        extra = extract_links_from_html(resp.text, num_results - len(collected))
                        for l in extra:
                            if l not in collected:
                                if site and site not in l:
                                    continue
                                collected.append(l)
                                if len(collected) >= num_results:
                                    break

                    break  # خروج من attempts عند 200

                elif resp.status_code in (429, 202):
                    wait = 2 ** attempt
                    print(f"⏳ Got {resp.status_code}, backoff {wait}s (attempt {attempt + 1})", flush=True)
                    time.sleep(wait)
                    continue
                else:
                    print("❌ DuckDuckGo returned status:", resp.status_code, flush=True)
                    break

            except Exception as e:
                print("⚠️ Error searching:", e, flush=True)
                traceback.print_exc()
                time.sleep(1)
                continue

        # قليل من التأخير بين الاستعلامات
        time.sleep(0.5)

    # تأكد أننا نعيد حتى لو كانت فارغة
    return collected[:num_results]


@app.route("/search", methods=["POST"])
def search():
    try:
        data = request.get_json(silent=True) or {}
        identifier = (data.get("identifier", "") or "").strip()
        print(f"🔍 Searching for: {identifier}", flush=True)

        if not identifier:
            return jsonify([])

        # تخزين البحث
        if client:
            try:
                client.execute(
                    "INSERT INTO users_log (username, os, country, ip, search) VALUES (?, ?, ?, ?, ?)",
                    ("server", "server", "Unknown", "0.0.0.0", identifier)
                )
            except Exception as e:
                print("DB insert error:", e)

        results = []

        for platform_name, domain in PLATFORMS.items():
            try:
                # جلب من الكاش أولاً
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
                    print(f"🗄️  Loaded {len(cached)} cached for {platform_name}", flush=True)
                    continue

                # بحث جديد: حاول الحصول على DESIRED_PER_PLATFORM
                links = duckduckgo_search_links(identifier, site=domain, num_results=DESIRED_PER_PLATFORM)

                if not links:
                    # فالنهاية جرب بحث عام بدون site: للقبض على أي رابط مرتبط بالاسم
                    links = duckduckgo_search_links(identifier, site=None, num_results=DESIRED_PER_PLATFORM)

                if not links:
                    print(f"⚠️ No links found for {platform_name} ({domain})", flush=True)

                for link in links:
                    results.append({"platform": platform_name, "link": link})
                    if client:
                        try:
                            client.execute(
                                "INSERT INTO search_cache (query, platform, link) VALUES (?, ?, ?)",
                                (identifier, platform_name, link)
                            )
                        except Exception as e:
                            print("Cache insert error:", e, flush=True)

                # تأخير بين المنصات
                time.sleep(REQUEST_DELAY)

            except Exception as e:
                print(f"Unhandled error searching {platform_name}:", e, flush=True)
                traceback.print_exc()
                continue

        print(f"🔚 Finished search for: {identifier} -> total results: {len(results)}", flush=True)
        return jsonify(results)

    except Exception as e:
        print("❌ Fatal error in /search:", e, flush=True)
        traceback.print_exc()
        return jsonify([])
    

if __name__ == "__main__":
    # لا تغيّر port هنا — Railway/hosting سيتحكم بالـ port عبر متغير البيئة PORT
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
