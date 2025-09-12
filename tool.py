# tool.py
"""
OSINT local search tool (DuckDuckGo primary + Bing fallback)
- Skips DDG 202 spam: if DDG returns 202 → fallback directly to Bing.
- Filters links strictly by platform domain.
- Logs minimal user info to SERVER_URL (no search results).
- Works with Python 3.12, uses requests + beautifulsoup4.
"""

import os
import time
import random
import platform
import requests
import urllib.parse
from bs4 import BeautifulSoup

# ====== CONFIG ======
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
MAX_RESULTS = 10
DUCK_URL = "https://html.duckduckgo.com/html/"
BING_URL = "https://www.bing.com/search"
REQUEST_TIMEOUT = 25
REQUEST_DELAY_BETWEEN_PLATFORMS = 1.2

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 13; SM-G990B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

IGNORE_EXTS = (
    ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".woff", ".woff2", ".ttf", ".ico", ".map", ".mp4", ".webm", ".otf"
)

session = requests.Session()

# -------- Helpers --------
def random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }

def is_valid_link_for_domain(link: str, domain: str) -> bool:
    if not link or not link.startswith(("http://", "https://")):
        return False
    lower = link.lower()
    if any(lower.endswith(ext) or ext in urllib.parse.urlparse(lower).path for ext in IGNORE_EXTS):
        return False
    if "r.bing.com" in lower or "bing.com/clk?" in lower:
        return False
    try:
        netloc = urllib.parse.urlparse(link).netloc.lower()
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        return netloc == domain or netloc.endswith("." + domain)
    except Exception:
        return False

def filter_links(links, domain):
    out = []
    for l in links:
        if is_valid_link_for_domain(l, domain) and l not in out:
            out.append(l)
        if len(out) >= MAX_RESULTS:
            break
    return out

# -------- DuckDuckGo search --------
def search_duckduckgo(query: str, site: str = None, max_results=MAX_RESULTS):
    q = f"{query} site:{site}" if site else query
    params = {"q": q}
    try:
        r = session.post(DUCK_URL, headers=random_headers(), data=params, timeout=REQUEST_TIMEOUT)
        if r.status_code == 202:
            # مباشرة fallback بلا Spam
            return []
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        collected = []
        for a in soup.select("a.result__a"):
            href = a.get("href")
            if href and href.startswith("http"):
                collected.append(href)
        return collected[:max_results]
    except:
        return []

# -------- Bing search --------
def search_bing(query: str, site: str = None, max_results=MAX_RESULTS):
    q = f"{query} site:{site}" if site else query
    params = {"q": q}
    try:
        r = session.get(BING_URL, headers=random_headers(), params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        collected = []
        for a in soup.select("li.b_algo h2 a"):
            href = a.get("href")
            if href and href.startswith("http"):
                collected.append(href)
        return collected[:max_results]
    except:
        return []

# -------- Main search --------
def search_username(username: str):
    results = {}
    payload = {
        "username": username,
        "system": platform.system(),
        "release": platform.release(),
    }
    try:
        session.post(SERVER_URL, json=payload, timeout=5)
    except:
        pass

    for platform_name, domain in PLATFORMS.items():
        print(f"🔍 Searching {platform_name}...")
        links = search_duckduckgo(username, site=domain)
        if not links:  # fallback مباشرة إذا فشل DDG أو رجع 202
            print(f"⚠️ No results from DuckDuckGo, using Bing fallback...")
            links = search_bing(username, site=domain)
        filtered = filter_links(links, domain)
        results[platform_name] = filtered
        print(f"✅ {platform_name}: {len(filtered)}/{MAX_RESULTS}")
        for l in filtered:
            print("   ", l)
        time.sleep(REQUEST_DELAY_BETWEEN_PLATFORMS)
    return results

# Run standalone
if __name__ == "__main__":
    user = input("[?] Enter username or first/last name: ").strip()
    if user:
        search_username(user)
