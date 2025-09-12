# tool.py
"""
OSINT tool using Qwant (requests + BeautifulSoup).
- Uses simple headers (rotates a little) and retries.
- Filters links strictly by platform domain and ignores static resources.
- Logs minimal user info to SERVER_URL (no search results).
Compatible with Python 3.12.
"""

import os
import time
import random
import platform
import requests
import urllib.parse
from bs4 import BeautifulSoup
from colorama import Fore, init, Style

init(autoreset=True)

# ===== CONFIG =====
SERVER_URL = os.getenv("SERVER_URL", "https://osint-tool-production.up.railway.app/log_search")
# If your Railway server uses another path, set SERVER_URL accordingly in env or replace above.

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
REQUEST_TIMEOUT = 30
MAX_RETRIES = 6
REQUEST_DELAY_BETWEEN_PLATFORMS = 1.0

QWANT_SEARCH_URL = "https://www.qwant.com/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]

# ignore static file extensions
IGNORE_EXTS = (
    ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".woff", ".woff2", ".ttf", ".ico", ".map", ".mp4", ".webm", ".m3u8"
)

session = requests.Session()


def random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        # minimal headers only
    }


def is_valid_link_for_domain(link: str, domain: str) -> bool:
    if not link or not link.startswith(("http://", "https://")):
        return False
    lower = link.lower()
    # exclude static resources
    for ext in IGNORE_EXTS:
        if lower.split("?")[0].endswith(ext):
            return False
    try:
        netloc = urllib.parse.urlparse(link).netloc.lower()
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        return netloc == domain or netloc.endswith("." + domain)
    except Exception:
        return False


def extract_links_from_qwant_html(html_text: str):
    """Extract absolute links from Qwant HTML page using bs4 fallback."""
    soup = BeautifulSoup(html_text, "html.parser")
    links = []
    # Qwant places results in <a> tags; be broad and gather anchors with href
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # Qwant sometimes uses internal redirect/JS links; try to fix common patterns:
        # - full url
        if href.startswith("http"):
            links.append(href)
        # - sometimes Qwant uses '/web?...' or '/search' local paths with target real urls as 'href' query — skip those
    # fallback: regex not necessary here; return unique preserving order
    seen = set()
    out = []
    for l in links:
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out


def qwant_search(query: str, site: str = None, max_results=MAX_RESULTS):
    """
    Perform search on Qwant for `query` (optionally site:<site>).
    Returns list of links (strings) filtered by site domain.
    """
    q = f"{query} site:{site}" if site else query
    params = {
        "q": q,
        "t": "web",
        "l": "en",  # language
    }
    links = []
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            headers = random_headers()
            resp = session.get(QWANT_SEARCH_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            status = resp.status_code
            # Detect block/challenge text quickly
            text_lower = (resp.text or "").lower()
            if "one last step" in text_lower or "captcha" in text_lower or "please verify" in text_lower:
                # Qwant presented a challenge, treat as blocked for this attempt
                print(Fore.YELLOW + f"⚠️ Qwant CAPTCHA/Protection detected, retrying in {attempt*3}s (attempt {attempt})")
                time.sleep(attempt * 3)
                continue
            if status != 200:
                print(Fore.YELLOW + f"⚠️ Qwant returned status {status}, retrying in {attempt*3}s (attempt {attempt})")
                time.sleep(attempt * 3)
                continue

            # parse links
            raw_links = extract_links_from_qwant_html(resp.text)
            # Filter out Qwant internal links (qwant.com) and keep only http(s) external links
            for rl in raw_links:
                if rl.startswith("http") and "qwant.com" not in rl:
                    links.append(rl)
                if len(links) >= max_results * 3:  # collect a bit more before final filter
                    break

            # final domain filter if site provided
            if site:
                filtered = [l for l in links if is_valid_link_for_domain(l, site)]
            else:
                filtered = links

            # deduplicate and trim to max_results
            out = []
            seen = set()
            for l in filtered:
                if l not in seen:
                    seen.add(l)
                    out.append(l)
                if len(out) >= max_results:
                    break

            # good result if at least one link
            if out:
                return out
            # otherwise retry a few times (maybe Qwant returned results inside JS)
            time.sleep(1 + attempt)
        except requests.RequestException as e:
            print(Fore.YELLOW + f"⚠️ Qwant request error: {e}, retrying in {attempt*2}s (attempt {attempt})")
            time.sleep(attempt * 2)
        except Exception as e:
            print(Fore.RED + f"⚠️ Qwant parse/unexpected error: {e}")
            break
    # exhausted retries -> return empty
    return []


def log_user_search(search_text: str):
    """Send minimal user info to SERVER_URL. Silent on failure."""
    try:
        ip = "0.0.0.0"
        try:
            ip = requests.get("https://api64.ipify.org?format=json", timeout=8).json().get("ip", ip)
        except Exception:
            pass
        payload = {
            "username": platform.node(),
            "os": platform.system() + " " + platform.release(),
            "country": "Unknown",
            "ip": ip,
            "search": search_text,
        }
        # send but don't wait too long
        requests.post(SERVER_URL, json=payload, timeout=8)
    except Exception:
        # silent
        pass


def run_checks(identifier: str):
    print(Fore.MAGENTA + "\n" + "=" * 60)
    print(Fore.MAGENTA + f"🔍 Start search about: {identifier}")
    print(Fore.MAGENTA + "=" * 60 + "\n")

    for platform_name, domain in PLATFORMS.items():
        print(Fore.YELLOW + f"🔍 Searching {platform_name}...")
        try:
            links = qwant_search(identifier, site=domain, max_results=MAX_RESULTS)
            count = len(links)
            if count == 0:
                print(Fore.RED + f"⚠️ No results from Qwant for {platform_name}")
            else:
                print(Fore.GREEN + f"✅ {platform_name}: {count}/{MAX_RESULTS}")
                for l in links[:MAX_RESULTS]:
                    print(Fore.CYAN + f"   {l}")
        except Exception as e:
            print(Fore.RED + f"❌ Error searching {platform_name}: {e}")
        # polite delay between platforms
        time.sleep(REQUEST_DELAY_BETWEEN_PLATFORMS)

    print(Fore.MAGENTA + "-" * 60 + "\n")


def main():
    print(Fore.GREEN + "OSINT Tool - Qwant search (simple mode)\n")
    while True:
        identifier = input(Fore.CYAN + "[?] Enter username or first/last name: " + Style.RESET_ALL).strip()
        if not identifier:
            print(Fore.RED + "[!] No input provided.")
            continue

        # log minimal user info (no results)
        log_user_search(identifier)

        run_checks(identifier)

        again = input(Fore.MAGENTA + "\n[?] Do you want to search again? (yes/no): ").strip().lower()
        if again not in ("yes", "y"):
            print(Fore.GREEN + "[✔] Exiting. Bye.")
            break


if __name__ == "__main__":
    main()
