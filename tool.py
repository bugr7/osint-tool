# tool.py
"""
OSINT local search tool (DuckDuckGo primary + Bing fallback)
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
MAX_DDG_RETRIES = 8
MAX_BING_RETRIES = 4
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
    if "r.bing.com" in lower or "bing.com/clk?" in lower or "microsoft.com" in lower and "bing.com" in lower:
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

# -------- DuckDuckGo search (HTML) --------
def search_duckduckgo(query: str, site: str = None, max_results=MAX
