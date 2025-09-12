"""
OSINT local search tool (Yahoo primary + Yandex fallback)
- Filters strictly by platform domain.
- Simple, clean, Python 3.12 compatible.
"""

import os
import requests
import urllib.parse
from bs4 import BeautifulSoup
import random
import time

# ====== CONFIG ======
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
REQUEST_TIMEOUT = 20
REQUEST_DELAY_BETWEEN_PLATFORMS = 1.0

# User-Agents rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; SM-G990B) Chrome/120.0.0.0 Mobile Safari/537.36",
]

IGNORE_EXTS = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg",
               ".ico", ".woff", ".woff2", ".ttf", ".map", ".mp4", ".webm", ".otf")

session = requests.Session()

# -------- Helpers --------
def random_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

def is_valid_link(link: str, domain: str) -> bool:
    if not link or not link.startswith(("http://", "https://")):
        return False
    lower = link.lower()
    if any(lower.endswith(ext) for ext in IGNORE_EXTS):
        return False
    try:
        netloc = urllib.parse.urlparse(link).netloc.lower()
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        return netloc == domain or netloc.endswith("." + domain)
    except:
        return False

def filter_links(links, domain):
    out = []
    for l in links:
        if is_valid_link(l, domain) and l not in out:
            out.append(l)
        if len(out) >= MAX_RESULTS:
            break
    return out

# -------- Search Engines --------
def search_yahoo(query: str, site: str):
    try:
        q = f"{query} site:{site}"
        url = f"https://search.yahoo.com/search?p={urllib.parse.quote(q)}"
        r = session.get(url, headers=random_headers(), timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        links = []

        # تجربة عدة selectors لياهو
        # أولاً: العناصر العادية التي تمثل النتائج
        # غالباً تلاقيها داخل <div class="Sr"> <a href="...">
        for a in soup.select("div.Sr a"):
            href = a.get("href")
            if href and href.startswith("http"):
                links.append(href)

        # إذا ما لقيتش نتيجة، نجرب selector آخر
        if not links:
            for a in soup.select("h3.title a"):
                href = a.get("href")
                if href and href.startswith("http"):
                    links.append(href)

        # فلترة حسب الدومين
        filtered = filter_links(links, site)
        return filtered

    except Exception as e:
        print(f"⚠️ Yahoo error: {e}")
        return []

def search_yandex(query: str, site: str):
    try:
        q = f"{query} site:{site}"
        url = f"https://yandex.com/search/?text={urllib.parse.quote(q)}"
        r = session.get(url, headers=random_headers(), timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        links = [a["href"] for a in soup.select("a.Link.Link_theme_normal") if a.get("href")]
        return filter_links(links, site)
    except:
        return []

def smart_search(query: str, site: str):
    results = search_yahoo(query, site)
    if results:
        return "Yahoo", results
    results = search_yandex(query, site)
    if results:
        return "Yandex", results
    return None, []

# -------- Main --------
def main():
    name = input("[?] Enter username or first/last name: ").strip()
    if not name:
        print("❌ No input provided.")
        return

    for platform, domain in PLATFORMS.items():
        print(f"🔍 Searching {platform}...")
        engine, links = smart_search(name, domain)
        if engine:
            print(f"✅ {platform} ({engine}): {len(links)}/{MAX_RESULTS}")
            for l in links:
                print("   ", l)
        else:
            print(f"❌ {platform}: no results.")
        time.sleep(REQUEST_DELAY_BETWEEN_PLATFORMS)

if __name__ == "__main__":
    main()

