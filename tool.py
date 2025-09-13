#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tool.py
DuckDuckGo OSINT scraper (requests + BeautifulSoup)
Best-effort strategy to avoid 0/10 results:
 - rotate user agents
 - small random delays and exponential backoff on retries
 - try multiple DuckDuckGo HTML endpoints (html + lite)
 - rebuild session / cookies between attempts
 - optional proxy support
"""

import requests
from bs4 import BeautifulSoup
import random
import time
import sys
from urllib.parse import quote_plus

# ---------------- Config ----------------
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

# maximum links per platform
NUM_RESULTS_PER_PLATFORM = 10

# how many total tries per platform (across endpoints + session resets)
MAX_TOTAL_ATTEMPTS = 6

# base timeout for requests
REQUEST_TIMEOUT = 15

# delay between platforms (helps avoid temporary blocks)
DELAY_BETWEEN_PLATFORMS = (1.2, 3.0)  # random.uniform between values (seconds)

# small delay between page fetch attempts (jitter)
DELAY_BETWEEN_ATTEMPTS = (0.5, 1.5)

# user agents rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
]

# DuckDuckGo endpoints to try (order matters: preferred first)
DDG_ENDPOINTS = [
    "https://html.duckduckgo.com/html/",  # standard HTML endpoint (POST)
    "https://lite.duckduckgo.com/lite/",  # lightweight endpoint (GET)
]

# Proxy configuration: None or a string like "http://127.0.0.1:8080" or "socks5://127.0.0.1:9050"
# You can also supply a list and the script will rotate them if you enable ROTATE_PROXIES = True
PROXIES = None
ROTATE_PROXIES = False
PROXY_LIST = []  # e.g. ["socks5://127.0.0.1:9050", "http://1.2.3.4:8080"]

# --------------- Helper functions ---------------

def build_proxies_for(proxy_url):
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}

def pick_proxy(attempt_index=0):
    if not PROXIES and not ROTATE_PROXIES:
        return None
    if ROTATE_PROXIES and PROXY_LIST:
        return build_proxies_for(PROXY_LIST[attempt_index % len(PROXY_LIST)])
    return build_proxies_for(PROXIES)

def new_session(user_agent=None, proxy=None):
    """
    Create a new requests.Session with given UA and optional proxies.
    Using a fresh session (new cookies) helps reduce persistent server-side detection.
    """
    s = requests.Session()
    ua = user_agent or random.choice(USER_AGENTS)
    s.headers.update({
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://duckduckgo.com/",
        "DNT": "1",
    })
    if proxy:
        s.proxies.update(proxy)
    return s

def parse_html_results_from_html_endpoint(html_text, max_results):
    """
    Parse the html.duckduckgo.com /result-like HTML pages.
    Look for .result__a anchors primarily, but also multi-fallback selectors.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    results = []

    # primary selector (common)
    for a in soup.select(".result__a"):
        href = a.get("href")
        title = a.get_text(strip=True)
        if href and href.startswith("http"):
            results.append((title, href))
        if len(results) >= max_results:
            return results

    # fallback selectors (some endpoints vary)
    for a in soup.select("a"):
        href = a.get("href")
        text = a.get_text(strip=True)
        if href and text and href.startswith("http") and "duckduckgo" not in href:
            # avoid internal duckduckgo links
            if (text, href) not in results:
                results.append((text, href))
        if len(results) >= max_results:
            return results

    return results

def parse_lite_results(html_text, max_results):
    """
    parse the lite endpoint where results appear as <a href="...">title</a>
    """
    soup = BeautifulSoup(html_text, "html.parser")
    results = []

    # the lite page often contains <a href="..."> with results, but also navigation links.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href and text and (href.startswith("http") or href.startswith("https")):
            # filter duckduckgo internal links
            if "duckduckgo.com" in href and not href.startswith("http"):
                continue
            if "duckduckgo" in href.lower():
                continue
            if (text, href) not in results:
                results.append((text, href))
        if len(results) >= max_results:
            return results
    return results

def clean_and_dedupe(items):
    seen = set()
    out = []
    for title, href in items:
        if not href:
            continue
        # normalize simple duplicates (strip params maybe)
        key = href.split("#")[0]
        if key not in seen:
            seen.add(key)
            out.append({"title": title or href, "href": href})
    return out

# --------------- Core search logic ---------------

def duckduckgo_search_links(query, site=None, num_results=10):
    """
    Best-effort DuckDuckGo search for `query` (optionally limited to site:domain).
    Tries multiple endpoints, rotates UA and optionally proxies, uses retries + backoff.
    Returns up to num_results results as list of dicts: {"title","href"}
    """
    target_query = f"{query} site:{site}" if site else query
    encoded_q = target_query  # don't double-encode; requests will handle form data

    accumulated = []
    attempt = 0

    # attempt across MAX_TOTAL_ATTEMPTS, rotating proxies/UA and endpoints
    while attempt < MAX_TOTAL_ATTEMPTS and len(accumulated) < num_results:
        endpoint_index = attempt % len(DDG_ENDPOINTS)
        endpoint = DDG_ENDPOINTS[endpoint_index]

        # pick proxy (if any)
        proxy = pick_proxy(attempt)

        # new session each attempt (fresh cookies)
        sess = new_session(user_agent=random.choice(USER_AGENTS), proxy=proxy)

        try:
            if endpoint.endswith("/html/"):
                # POST form
                resp = sess.post(endpoint, data={"q": target_query}, timeout=REQUEST_TIMEOUT)
                # sometimes server returns 403 or a block page, check status
                if resp.status_code != 200:
                    # backoff and retry
                    raise requests.RequestException(f"HTTP {resp.status_code} from {endpoint}")
                parsed = parse_html_results_from_html_endpoint(resp.text, num_results)
            else:
                # use GET for lite endpoint, encode query in URL
                q = quote_plus(target_query)
                url = endpoint + "?q=" + q
                resp = sess.get(url, timeout=REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    raise requests.RequestException(f"HTTP {resp.status_code} from {endpoint}")
                parsed = parse_lite_results(resp.text, num_results)

            # extend accumulated with parsed items avoiding duplicates right away
            for title, href in parsed:
                if href and href.startswith("http"):
                    accumulated.append((title, href))
                if len(accumulated) >= num_results:
                    break

            # if we got something, small pause (helps avoid hitting rate limit)
            if parsed:
                time.sleep(random.uniform(0.15, 0.6))

        except Exception as e:
            # on error, print debug and backoff
            # do not exit: we will retry with different session/endpoint/proxy
            # keep messages succinct
            # (silent option could be added later)
            # print debug to stderr so user can see issues
            print(f"[!] attempt {attempt+1}/{MAX_TOTAL_ATTEMPTS} error: {e}", file=sys.stderr)

            # exponential backoff with jitter
            backoff = (2 ** attempt) * 0.25
            jitter = random.uniform(0.3, 1.0)
            time.sleep(backoff + jitter)

        finally:
            # close session to drop sockets/cookies
            try:
                sess.close()
            except:
                pass

        attempt += 1

    # clean & dedupe and limit to desired number
    cleaned = clean_and_dedupe(accumulated)
    return cleaned[:num_results]

# --------------- Runner across platforms ---------------

def run_checks(identifier):
    print("=" * 70)
    print(f"Starting search for: {identifier!s}")
    print("=" * 70)
    for platform_name, domain in PLATFORMS.items():
        print(f"\n--- {platform_name} ({domain}) ---")
        # random small sleep before platform to vary request pattern
        time.sleep(random.uniform(0.2, 0.8))
        results = duckduckgo_search_links(identifier, site=domain, num_results=NUM_RESULTS_PER_PLATFORM)
        count = len(results)
        print(f"{platform_name}: {count}/{NUM_RESULTS_PER_PLATFORM}")
        if count:
            for i, r in enumerate(results, 1):
                print(f"{i:2d}. {r['title']}")
                print(f"     {r['href']}")
        else:
            print("   ⚠️ No results obtained for this platform (attempted multiple strategies).")
        # delay between platforms (reduce chance of temporary block)
        time.sleep(random.uniform(*DELAY_BETWEEN_PLATFORMS))

# --------------- Main ---------------

def main():
    print(r"""
 /$$$$$$$                                   /$$$$$$$$
| $$__  $$                                 |_____ $$/
| $$  \ $$ /$$   /$$  /$$$$$$         /$$$$$$   /$$/
| $$$$$$$/| $$  | $$ /$$__  $$ /$$$$$$|____  $$ /$$/
| $$__  $$| $$  | $$| $$  \__/|______/ /$$$$$$$| $$
| $$  \ $$| $$  | $$| $$       /$$    /$$__  $$| $$
| $$  | $$|  $$$$$$/| $$      | $$   |  $$$$$$$| $$
|__/  |__/ \______/ |__/      |__/    \_______/|__/
""")
    print("DuckDuckGo OSINT — requests + BeautifulSoup (best-effort)\n")

    # optional: let user set proxy at runtime
    global PROXIES, ROTATE_PROXIES, PROXY_LIST
    proxy_input = input("Enter proxy (http://... or socks5://...) or press Enter to skip: ").strip()
    if proxy_input:
        # allow comma-separated list to enable rotation
        if "," in proxy_input:
            PROXY_LIST = [p.strip() for p in proxy_input.split(",") if p.strip()]
            ROTATE_PROXIES = True
            PROXIES = None
            print(f"Proxy rotation enabled with {len(PROXY_LIST)} proxies.")
        else:
            PROXIES = proxy_input
            ROTATE_PROXIES = False
            PROXY_LIST = []

    while True:
        identifier = input("\n[?] Enter username or full name (or type 'exit' to quit): ").strip()
        if not identifier:
            continue
        if identifier.lower() in ("exit", "quit"):
            print("Exiting. Goodbye.")
            break
        run_checks(identifier)

if __name__ == "__main__":
    main()
