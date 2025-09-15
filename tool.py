#!/usr/bin/env python3
# tool.py
# OSINT simple scraper using Bing + requests + bs4
# Supports: youtube, tiktok, reddit, linkedin, facebook, instagram
# Saves results to results.txt and results.csv
# Usage: python tool.py

import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import os
import sys
from urllib.parse import urlparse, parse_qs, urlunparse

# ----------------- config -----------------
PLATFORMS = {
    "youtube": ["youtube.com", "youtu.be"],
    "tiktok": ["tiktok.com"],
    "reddit": ["reddit.com"],
    "linkedin": ["linkedin.com"],
    "facebook": ["facebook.com", "fb.com"],
    "instagram": ["instagram.com"]
}
RESULTS_PER_PLATFORM = 5
REQUEST_TIMEOUT = 12
MAX_RETRIES = 2
MIN_DELAY = 1.2
MAX_DELAY = 3.0
# Optional proxies via env var PROXY (format http://IP:PORT or socks5://IP:PORT)
PROXY = os.environ.get("PROXY")  # e.g. "http://51.79.50.22:9300"
# ------------------------------------------

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
]

session = requests.Session()
if PROXY:
    session.proxies.update({"http": PROXY, "https": PROXY})


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.bing.com/"
    }


def normalize_url(u):
    """
    Basic normalization: remove common tracking query params like utm_*, fbclid, gclid
    """
    try:
        p = urlparse(u)
        qs = parse_qs(p.query, keep_blank_values=True)
        filtered = {k: v for k, v in qs.items() if not (
            k.startswith("utm_") or k in ("fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "mkt_tok"))}
        # rebuild query string
        if filtered:
            new_query = "&".join(f"{k}={v[0]}" for k, v in filtered.items())
        else:
            new_query = ""
        cleaned = urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
        return cleaned
    except Exception:
        return u


def extract_from_bing_html(html_text, platform_domains, limit):
    soup = BeautifulSoup(html_text, "html.parser")
    results = []
    # Bing main results are usually in li.b_algo > h2 > a
    for li in soup.select("li.b_algo"):
        a = li.select_one("h2 > a[href]")
        if not a:
            # fallback: any <a> with href inside the li
            a = li.select_one("a[href]")
        if a:
            href = a.get("href").strip()
            # ensure it's absolute
            if not href.startswith("http"):
                continue
            for domain in platform_domains:
                if domain in href:
                    cleaned = normalize_url(href)
                    if cleaned not in results:
                        results.append(cleaned)
                    break
        if len(results) >= limit:
            break
    return results


def bing_search(query, platform, limit=5):
    q = f"{query} site:{platform}.com"
    url = f"https://www.bing.com/search?q={requests.utils.requote_uri(q)}"
    tries = 0
    while tries <= MAX_RETRIES:
        tries += 1
        try:
            resp = session.get(url, headers=get_headers(), timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                # server-side block or temp problem
                # return empty to let caller decide
                return []
            res = extract_from_bing_html(resp.text, PLATFORMS[platform], limit)
            return res
        except requests.RequestException:
            if tries > MAX_RETRIES:
                return []
            time.sleep(1 + tries)
    return []


def save_results_text(all_results, filename="results.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for platform, links in all_results.items():
            f.write(f"=== {platform.upper()} ===\n")
            if not links:
                f.write("NO RESULTS\n\n")
                continue
            for l in links:
                f.write(l + "\n")
            f.write("\n")


def save_results_csv(all_results, filename="results.csv"):
    rows = []
    for platform, links in all_results.items():
        if not links:
            rows.append([platform, ""])
        else:
            for l in links:
                rows.append([platform, l])
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        w = csv.writer(csvfile)
        w.writerow(["platform", "url"])
        w.writerows(rows)


def osint_tool(query):
    all_results = {}
    print()
    for p in PLATFORMS.keys():
        print(f"🔎 البحث في {p.capitalize()}...")
        results = bing_search(query, p, limit=RESULTS_PER_PLATFORM)
        if results:
            for r in results:
                print("👉", r)
        else:
            print("❌ لا توجد نتائج.")
        all_results[p] = results
        # random delay
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    # save
    save_results_text(all_results)
    save_results_csv(all_results)
    print("\n✅ النتائج تحفظت في results.txt و results.csv\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        try:
            query = input("[?] أدخل الاسم واللقب أو اسم المستخدم: ").strip()
        except KeyboardInterrupt:
            print("\nBye")
            sys.exit(0)
    if not query:
        print("لا شيء للدخول.")
        sys.exit(1)
    osint_tool(query)
