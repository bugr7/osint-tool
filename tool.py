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
# platforms to search (display order)
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
REQUEST_TIMEOUT = 25  # timeout for HTTP requests
MAX_DDG_RETRIES = 8
MAX_BING_RETRIES = 4
REQUEST_DELAY_BETWEEN_PLATFORMS = 1.2

# rotate user agents to reduce chance of blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 13; SM-G990B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

# static/resource file extensions to ignore
IGNORE_EXTS = (
    ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".woff", ".woff2", ".ttf", ".ico", ".map", ".mp4", ".webm", ".otf"
)

session = requests.Session()


# -------- Helpers --------
def random_headers():
    return {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}


def is_valid_link_for_domain(link: str, domain: str) -> bool:
    """Return True if link is a http(s) URL and belongs to domain (including subdomains),
       and is not a static resource or a known search redirect (r.bing.com)."""
    if not link or not link.startswith(("http://", "https://")):
        return False
    lower = link.lower()
    if any(lower.endswith(ext) or ext in urllib.parse.urlparse(lower).path for ext in IGNORE_EXTS):
        return False
    if "r.bing.com" in lower or "bing.com/clk?" in lower or "microsoft.com" in lower and "bing.com" in lower:
        return False
    # ensure domain match (domain may appear as subdomain)
    try:
        netloc = urllib.parse.urlparse(link).netloc.lower()
        # strip port if present
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        # domain match if netloc equals domain or endswith .domain
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
def search_duckduckgo(query: str, site: str = None, max_results=MAX_RESULTS):
    q = f"{query} site:{site}" if site else query
    params = {"q": q}
    headers = random_headers()
    collected = []

    for attempt in range(1, MAX_DDG_RETRIES + 1):
        try:
            resp = session.get(DUCK_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            status = resp.status_code
            if status == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # standard duckduckgo selector
                anchors = soup.select("a.result__a")
                if not anchors:
                    anchors = soup.find_all("a")
                for a in anchors:
                    href = a.get("href") or a.get("data-href") or a.get("data-redirect")
                    if not href:
                        continue
                    # duckduckgo sometimes wraps target in uddg=
                    if "uddg=" in href:
                        try:
                            # extract uddg param
                            parsed = urllib.parse.urlparse(href)
                            qpars = urllib.parse.parse_qs(parsed.query)
                            uddg = qpars.get("uddg") or qpars.get("u")
                            if uddg:
                                href = urllib.parse.unquote(uddg[0])
                        except Exception:
                            pass
                    if href and href not in collected:
                        collected.append(href)
                        if len(collected) >= max_results * 2:  # collect a bit more then filter
                            break
                # Return what we got (may be empty)
                return collected
            elif status == 202:
                # service busy / blocked -> exponential backoff
                wait = min(30, attempt * 3)
                print(f"⚠️ DuckDuckGo 202, retrying in {wait}s (attempt {attempt})")
                time.sleep(wait)
                headers = random_headers()  # rotate UA
                continue
            elif status in (429,):
                wait = min(60, attempt * 5)
                print(f"⚠️ DuckDuckGo {status}, rate-limited. Waiting {wait}s (attempt {attempt})")
                time.sleep(wait)
                headers = random_headers()
                continue
            else:
                print(f"❌ DuckDuckGo returned {status}, stopping DDG attempts for this query.")
                break
        except requests.RequestException as e:
            wait = min(30, attempt * 3)
            print(f"⚠️ DuckDuckGo request error: {e} — retrying in {wait}s (attempt {attempt})")
            time.sleep(wait)
            headers = random_headers()
            continue
    return collected


# -------- Bing fallback (HTML) --------
def search_bing(query: str, site: str = None, max_results=MAX_RESULTS):
    q = f"{query} site:{site}" if site else query
    params = {"q": q, "count": str(max_results * 2)}
    headers = random_headers()
    collected = []
    for attempt in range(1, MAX_BING_RETRIES + 1):
        try:
            resp = session.get(BING_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Bing results are usually in li.b_algo h2 a
                items = soup.select("li.b_algo h2 a")
                if not items:
                    # fallback try generic anchors
                    items = soup.find_all("a")
                for a in items:
                    href = a.get("href")
                    if href and href not in collected:
                        collected.append(href)
                        if len(collected) >= max_results * 3:
                            break
                return collected
            else:
                wait = min(20, attempt * 3)
                print(f"⚠️ Bing returned {resp.status_code}, retrying in {wait}s (attempt {attempt})")
                time.sleep(wait)
                headers = random_headers()
        except requests.RequestException as e:
            wait = min(20, attempt * 3)
            print(f"⚠️ Bing request error: {e} — retrying in {wait}s (attempt {attempt})")
            time.sleep(wait)
            headers = random_headers()
    return collected


# -------- logging minimal user info to server (Railway -> Turso) --------
def log_user_search(search_text: str):
    # gather minimal info
    try:
        ip = session.get("https://api64.ipify.org?format=json", timeout=8).json().get("ip", "0.0.0.0")
    except Exception:
        ip = "0.0.0.0"
    payload = {
        "username": platform.node(),
        "os": platform.system() + " " + platform.release(),
        "country": "Unknown",
        "ip": ip,
        "search": search_text,
    }
    try:
        session.post(SERVER_URL, json=payload, timeout=12)
    except Exception as e:
        # logging should not break the tool
        print(f"⚠️ Failed to log to server: {e}")


# -------- main search orchestration per platform --------
def search_identifier(identifier: str):
    all_results = []
    print(f"\n🔎 Start search for: {identifier}\n")
    for platform_name, domain in PLATFORMS.items():
        print(f"🔍 Searching {platform_name}...")
        # 1) try DuckDuckGo (primary)
        ddg_raw = search_duckduckgo(identifier, site=domain, max_results=MAX_RESULTS)
        ddg_filtered = filter_links(ddg_raw, domain)
        if len(ddg_filtered) >= MAX_RESULTS:
            results = ddg_filtered[:MAX_RESULTS]
            source = "DuckDuckGo"
        else:
            # If insufficient or empty, try Bing fallback
            if ddg_raw:
                # still might include some valid items
                partial = ddg_filtered
            else:
                partial = []
            print(f"⚠️ No/insufficient from DuckDuckGo for {platform_name}. Using Bing fallback...")
            bing_raw = search_bing(identifier, site=domain, max_results=MAX_RESULTS)
            bing_filtered = filter_links(bing_raw, domain)
            # merge unique, prefer DDG order then Bing
            merged = []
            for l in (partial + bing_filtered):
                if l not in merged:
                    merged.append(l)
                if len(merged) >= MAX_RESULTS:
                    break
            results = merged
            source = "DuckDuckGo+Bing" if merged else "none"

        if results:
            print(f"✅ {platform_name}: {len(results)}/{MAX_RESULTS} (source: {source})")
            for r in results:
                print(f"   {r}")
                all_results.append({"platform": platform_name, "link": r})
        else:
            print(f"❌ {platform_name}: 0/{MAX_RESULTS} — No results found (source: {source})")

        time.sleep(REQUEST_DELAY_BETWEEN_PLATFORMS)

    print(f"\n🔚 Search finished. Total found: {len(all_results)} links.\n")
    return all_results


# -------- CLI --------
def main():
    print("OSINT tool — DuckDuckGo primary + Bing fallback")
    while True:
        identifier = input("[?] Enter username or first/last name: ").strip()
        if not identifier:
            print("❌ No input provided.")
            continue

        # log minimal user info (does not send results)
        log_user_search(identifier)

        try:
            results = search_identifier(identifier)
            # optionally: you could POST results to a different endpoint
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting.")
            break
        except Exception as e:
            print(f"⚠️ Unexpected error during search: {e}")

        again = input("\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print("✔ Exiting.")
            break


if __name__ == "__main__":
    main()
