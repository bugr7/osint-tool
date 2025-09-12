# tool.py
import os
import platform
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

# يمكن تحديد رابط السيرفر من متغير بيئة SERVER_URL أو يستخدم الافتراضي
SERVER_URL = os.getenv("SERVER_URL", "https://osint-tool-production.up.railway.app/log_search")

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
MAX_RESULTS = int(os.getenv("MAX_RESULTS", 10))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 6))  # محاولة أكثر قبل الاستسلام
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", 25.0))

# قائمة User-Agents للتدوير لتقليل الحجب
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

session = requests.Session()


def _set_random_ua():
    ua = random.choice(USER_AGENTS)
    session.headers.update({"User-Agent": ua})


def log_user_search(search_text):
    """إرسال بيانات البحث إلى السيرفر (Railway -> Turso)."""
    try:
        ip = requests.get("https://api64.ipify.org?format=json", timeout=8).json().get("ip", "0.0.0.0")
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
        # إرسال بدون انتظار نتيجة كبيرة (timeout قصير)
        requests.post(SERVER_URL, json=data, timeout=10)
    except Exception as e:
        # لا نوقف البحث إذا فشل التسجيل
        print("⚠️ Failed to log user search:", e)


def _extract_links_from_ddg_html(resp_text):
    """محاولة استخراج الروابط من HTML الخاص بـ DuckDuckGo."""
    soup = BeautifulSoup(resp_text, "html.parser")
    links = []

    # أفضل اختيار لعناصر النتائج
    anchors = soup.select("a.result__a")
    if not anchors:
        anchors = soup.find_all("a")

    for a in anchors:
        href = a.get("href") or ""
        link = None
        if href:
            # حالة uddg (DuckDuckGo يشفر الرابط)
            if "uddg=" in href:
                # نحاول فك قيمة الuddg
                try:
                    q = urllib.parse.urlparse(href).query
                    params = urllib.parse.parse_qs(q)
                    if "uddg" in params:
                        link = urllib.parse.unquote(params["uddg"][0])
                except Exception:
                    link = None
            else:
                link = href

        # أحيانا الرابط محفوظ في data-href أو data-redirect
        if not link:
            data_href = a.get("data-href") or a.get("data-redirect")
            if data_href:
                link = data_href

        if link and link.startswith("http") and "duckduckgo" not in link:
            if link not in links:
                links.append(link)

    # فالباك بسيط: regex href
    if not links:
        import re
        found = re.findall(r'href="(https?://[^"]+)"', resp_text)
        for link in found:
            if "duckduckgo" not in link and link not in links:
                links.append(link)

    return links


def duckduckgo_search(query, site=None, max_results=MAX_RESULTS):
    """حاول جلب نتائج من DuckDuckGo HTML endpoint مع retries وbackoff.
       إذا نجح يعيد قائمة الروابط (حتى max_results)."""
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    links = []

    for attempt in range(MAX_RETRIES):
        _set_random_ua()
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT)
            status = getattr(resp, "status_code", None)
            if status == 200:
                candidate = _extract_links_from_ddg_html(resp.text)
                for l in candidate:
                    if l not in links:
                        links.append(l)
                    if len(links) >= max_results:
                        break
                if links:
                    return links[:max_results]
                # لو لم نجد شيئا، نجرب محاولات أخرى
            elif status in (202, 429):
                wait = (attempt + 1) * 3
                print(f"⚠️ DuckDuckGo {status}, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue
            else:
                print(f"❌ DuckDuckGo returned status: {status}")
                # حالات أخرى نخرج ونجرب fallback
                break
        except Exception as e:
            print("⚠️ DuckDuckGo request error:", e)
            time.sleep(2)

    return links  # قد تكون فارغة -> fallback يحدث خارجاً


def _extract_links_from_bing_html(resp_text):
    soup = BeautifulSoup(resp_text, "html.parser")
    links = []

    # Bing: عناصر النتائج غالبا داخل li.b_algo a  أو h2 > a
    results = soup.select("li.b_algo h2 a")
    if not results:
        results = soup.select("li.b_algo a")

    for a in results:
        href = a.get("href")
        if href and href.startswith("http"):
            if href not in links:
                links.append(href)

    # فالباك بسيط
    if not links:
        import re
        found = re.findall(r'href="(https?://[^"]+)"', resp_text)
        for link in found:
            if link not in links:
                links.append(link)

    return links


def bing_search(query, site=None, max_results=MAX_RESULTS):
    """Fallback: scrape Bing search results page."""
    search_query = f"{query} site:{site}" if site else query
    url = "https://www.bing.com/search"
    params = {"q": search_query, "count": str(max_results * 2)}
    links = []

    for attempt in range(3):
        _set_random_ua()
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT)
            if resp.status_code == 200:
                candidate = _extract_links_from_bing_html(resp.text)
                for l in candidate:
                    if l not in links:
                        links.append(l)
                    if len(links) >= max_results:
                        break
                return links[:max_results]
            else:
                time.sleep(1 + attempt)
        except Exception as e:
            print("⚠️ Bing request error:", e)
            time.sleep(1)

    return links


def search_identifier(identifier):
    results_total = []

    for platform_name, domain in PLATFORMS.items():
        print(f"🔍 Searching {platform_name}...")
        links = duckduckgo_search(identifier, site=domain, max_results=MAX_RESULTS)
        # لو DuckDuckGo أعطى نتائج قليلة أو صفر، نستخدم Bing كـ fallback
        if not links or len(links) < MAX_RESULTS:
            # نجرب زيادة المحاولات لـ DuckDuckGo سريعا مرة أخرى (محاولة أخيرة)
            extra = duckduckgo_search(identifier, site=domain, max_results=MAX_RESULTS)
            for l in extra:
                if l not in links:
                    links.append(l)
                    if len(links) >= MAX_RESULTS:
                        break

        if not links:
            print(f"⚠️ No/insufficient from DuckDuckGo for {platform_name}. Using Bing fallback...")
            links = bing_search(identifier, site=domain, max_results=MAX_RESULTS)

        count = len(links)
        print(f"✅ {platform_name}: {count}/{MAX_RESULTS}" if count else f"❌ {platform_name}: 0/{MAX_RESULTS}")
        for link in links[:MAX_RESULTS]:
            print(f"   {link}")
            results_total.append({"platform": platform_name, "link": link})

        # تأخير بسيط لتخفيف الحجب
        time.sleep(REQUEST_DELAY + random.random() * 0.5)

    return results_total


def main():
    print("OSINT tool - local scraping mode (DDG primary, Bing fallback)")
    while True:
        identifier = input("[?] Enter username or first/last name: ").strip()
        if not identifier:
            print("❌ No input provided.")
            continue

        # Log to server (Railway -> Turso) - لا نرسل نتائج DuckDuckGo إلى السيرفر
        log_user_search(identifier)

        results = search_identifier(identifier)
        total = len(results)
        print(f"\n🔎 Total links collected: {total}\n")

        again = input("[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print("✔ Exiting.")
            break


if __name__ == "__main__":
    main()
