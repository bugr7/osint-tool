#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
osint_tool_full.py — نسخة متكاملة قوية لأداة OSINT (Multi-engine, Proxy rotation, UA rotation, retries)
==========================================================================================
Credits / Inspired by: awesome-osint lists and common OSINT tool patterns.
Purpose: جمع روابط علنية من منصات اجتماعية (YouTube, TikTok, Reddit, LinkedIn, Facebook, Instagram)
Features:
 - محركات: Bing (أساسي) ، DuckDuckGo (html) و Startpage كـ fallback
 - User-Agent rotation, jitter delays, exponential backoff, retry logic
 - Optional cloudscraper use (if installed) to bypass some protections; fallback to requests
 - Proxy rotation (file / ENV / single proxy) + Tor support (socks5://127.0.0.1:9050)
 - Query permutations to increase match chance
 - Strong filtering: فقط روابط واضحة (http/https) و التي تنتمي للدومين المطلوب
 - فك ترميز روابط DuckDuckGo (uddg) حتى تظهر روابط مباشرة وصافية
 - تَخزين النتائج إلى results.txt / results.csv / results.json
 - Interactive input: يطلب "أدخل اسم المستخدم أو الاسم الكامل" عند التشغيل
Usage examples:
  python osint_tool_full.py
  python osint_tool_full.py "elon musk" --results 10 --verbose
  python osint_tool_full.py "username" --proxies-file proxies.txt --tor
Notes & Warnings:
 - Use responsibly. Respect websites' terms of service and local laws.
 - For very heavy or repeated usage, use paid proxy pools and/or official APIs (YouTube Data API, Reddit API).
 - If cloudscraper import fails on your system, run with --no-cloudscraper or fix package versions:
     pip install --upgrade requests urllib3 requests_toolbelt cloudscraper
"""

import os
import sys
import time
import random
import json
import csv
import argparse
import traceback
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs, unquote, quote_plus

# Try import cloudscraper, but fall back to requests if not available
HAS_CLOUDSCRAPER = False
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except Exception:
    pass

import requests
from bs4 import BeautifulSoup
from itertools import permutations

# ---------------- CONFIG ----------------
PLATFORMS = {
    "youtube": ["youtube.com", "youtu.be"],
    "tiktok": ["tiktok.com"],
    "reddit": ["reddit.com"],
    "linkedin": ["linkedin.com"],
    "facebook": ["facebook.com", "fb.com"],
    "instagram": ["instagram.com"]
}

DEFAULT_RESULTS_PER_PLATFORM = 10
DEFAULT_MIN_DELAY = 0.8
DEFAULT_MAX_DELAY = 2.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.8

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    # add more UAs if wanted
]

ENGINES = {
    "bing": {
        "name": "Bing",
        "url": "https://www.bing.com/search?q={}",
        "parser": "parse_bing"
    },
    "ddg_html": {
        "name": "DuckDuckGo (html)",
        "url": "https://html.duckduckgo.com/html/?q={}",
        "parser": "parse_ddg_html"
    },
    "startpage": {
        "name": "Startpage",
        "url": "https://www.startpage.com/sp/search?q={}",
        "parser": "parse_startpage"
    }
}

# ---------------- Helpers ----------------
def choose_ua() -> str:
    return random.choice(USER_AGENTS)

def jitter_sleep(min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY):
    time.sleep(random.uniform(min_delay, max_delay))

def ensure_scheme(u: str) -> str:
    if not u:
        return u
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return "https://" + u

def normalize_url(u: str) -> str:
    if not u:
        return u
    u = u.strip()
    # If contains uddg=... (DuckDuckGo redirect), try extract and unquote
    try:
        if "uddg=" in u:
            # try parse query to get uddg
            parsed = urlparse(u)
            q = parse_qs(parsed.query)
            if "uddg" in q and q["uddg"]:
                return unquote(q["uddg"][0])
            # fallback: find uddg= pattern in string
            idx = u.find("uddg=")
            if idx != -1:
                frag = u[idx+5:]
                # remove potential trailing &...
                frag = frag.split("&",1)[0]
                return unquote(frag)
        # if contains /l/?uddg= style
        if "duckduckgo.com/l/?" in u and "uddg=" in u:
            parsed = urlparse(u)
            q = parse_qs(parsed.query)
            if "uddg" in q:
                return unquote(q["uddg"][0])
    except Exception:
        pass
    return unquote(u)

def dedupe_keep_order(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        if not u:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

def filter_platform_urls(urls: List[str], platform_domains: List[str]) -> List[str]:
    out = []
    for u in urls:
        if not u:
            continue
        u = ensure_scheme(u)
        # skip obviously bad patterns
        if u.startswith("https://go.microsoft.com") or "/search?q=" in u or "do/settings" in u:
            continue
        # normalize duckduckgo encoded
        u = normalize_url(u)
        u = ensure_scheme(u)
        # check domain membership
        parsed = urlparse(u)
        host = parsed.netloc.lower()
        for d in platform_domains:
            if d in host:
                out.append(u)
                break
    return dedupe_keep_order(out)

# ---------------- HTTP Client ----------------
class HttpClient:
    def __init__(self, proxy: Optional[str] = None, use_cloudscraper: bool = False):
        self.use_cloudscraper = use_cloudscraper and HAS_CLOUDSCRAPER
        self.session = None
        if self.use_cloudscraper:
            try:
                self.session = cloudscraper.create_scraper()
            except Exception:
                self.use_cloudscraper = False
                self.session = requests.Session()
        else:
            self.session = requests.Session()
        # set proxy if provided
        if proxy:
            self.session.proxies.update({"http": proxy, "https": proxy})

    def get(self, url: str, headers: dict = None, timeout: int = 15):
        headers = headers or {}
        return self.session.get(url, headers=headers, timeout=timeout)

# ---------------- Parsers ----------------
def parse_bing(html: str, platform_domains: List[str], limit: int) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    # Common bing result anchors
    for a in soup.select("li.b_algo h2 a, h2 a"):
        href = a.get("href")
        if not href:
            continue
        href = ensure_scheme(href)
        for d in platform_domains:
            if d in href:
                results.append(href)
                break
        if len(results) >= limit:
            break
    # fallback: any anchor
    if not results:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href:
                continue
            for d in platform_domains:
                if d in href:
                    results.append(ensure_scheme(href))
            if len(results) >= limit:
                break
    return dedupe_keep_order(results)[:limit]

def parse_ddg_html(html: str, platform_domains: List[str], limit: int) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    # anchors with result__a or direct hrefs
    for a in soup.select("a.result__a, a.result__snippet, a[href]"):
        href = a.get("href")
        if not href:
            continue
        # if uddg param is present inside href string, normalize
        if "uddg=" in href or "duckduckgo.com/l/?" in href:
            try:
                real = normalize_url(href)
                real = ensure_scheme(real)
                for d in platform_domains:
                    if d in real:
                        results.append(real)
                        break
            except Exception:
                continue
        else:
            href_full = ensure_scheme(href)
            for d in platform_domains:
                if d in href_full:
                    results.append(href_full)
                    break
        if len(results) >= limit:
            break
    return dedupe_keep_order(results)[:limit]

def parse_startpage(html: str, platform_domains: List[str], limit: int) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for sel in ["a.w-gl__result-title", "a.result-url", "a[href]"]:
        for a in soup.select(sel):
            href = a.get("href")
            if not href:
                continue
            href = ensure_scheme(href)
            for d in platform_domains:
                if d in href:
                    results.append(href)
                    break
            if len(results) >= limit:
                break
        if results:
            break
    return dedupe_keep_order(results)[:limit]

# ---------------- Engine request + parse ----------------
def engine_request_and_parse(engine_key: str, query_encoded: str, platform: str, client: HttpClient, results_limit: int, timeout=15, verbose=False) -> List[str]:
    engine = ENGINES.get(engine_key)
    if not engine:
        return []
    url = engine["url"].format(query_encoded)
    headers = {
        "User-Agent": choose_ua(),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.bing.com/"
    }

    attempt = 0
    backoff = DEFAULT_BACKOFF_FACTOR
    last_exc = None
    while attempt < DEFAULT_MAX_RETRIES:
        attempt += 1
        try:
            resp = client.get(url, headers=headers, timeout=timeout)
            status = getattr(resp, "status_code", None)
            content = getattr(resp, "text", "")
            if status and status != 200:
                last_exc = Exception(f"HTTP {status} from {engine_key}")
                # show 202 block info if verbose
                if verbose:
                    print(f"[!] {engine['name']} returned HTTP {status} (attempt {attempt}/{DEFAULT_MAX_RETRIES})")
                time.sleep(backoff + random.random())
                backoff *= DEFAULT_BACKOFF_FACTOR
                continue

            parser_name = engine["parser"]
            platform_domains = PLATFORMS[platform]
            if parser_name == "parse_bing":
                found = parse_bing(content, platform_domains, results_limit)
            elif parser_name == "parse_ddg_html":
                found = parse_ddg_html(content, platform_domains, results_limit)
            elif parser_name == "parse_startpage":
                found = parse_startpage(content, platform_domains, results_limit)
            else:
                found = []
            return found
        except KeyboardInterrupt:
            raise
        except Exception as e:
            last_exc = e
            if verbose:
                print(f"[!] Exception calling {engine['name']}: {e} (attempt {attempt}/{DEFAULT_MAX_RETRIES})")
            time.sleep(backoff + random.random())
            backoff *= DEFAULT_BACKOFF_FACTOR
            continue
    if last_exc and verbose:
        print(f"[!] Engine {engine_key} failed after {DEFAULT_MAX_RETRIES} attempts: {last_exc}")
    return []

# ---------------- Query permutations ----------------
def generate_query_variations(name: str, extras: Optional[List[str]] = None, cap: int = 60) -> List[str]:
    name = name.strip()
    tokens = [t for t in name.split() if t]
    variations = []
    if not tokens:
        return variations
    # original and quoted
    variations.append(name)
    variations.append('"' + name + '"')
    # permutations up to 3 tokens to avoid explosion
    max_len = min(3, len(tokens))
    seen = set()
    for r in range(1, max_len + 1):
        for p in permutations(tokens, r):
            s = " ".join(p)
            if s not in seen:
                variations.append(s)
                seen.add(s)
                variations.append('"' + s + '"')
    extras = extras or []
    for base in list(variations):
        for ex in extras:
            v = f"{base} {ex}"
            if v not in seen:
                variations.append(v); seen.add(v)
    # dedupe & cap
    out = []
    for v in variations:
        if v not in out:
            out.append(v)
        if len(out) >= cap:
            break
    return out

# ---------------- Core search ----------------
def osint_search(name_or_username: str,
                 platforms: Optional[List[str]] = None,
                 results_per_platform: int = DEFAULT_RESULTS_PER_PLATFORM,
                 engines_priority: Optional[List[str]] = None,
                 proxies: Optional[List[str]] = None,
                 tor: bool = False,
                 extras_for_variations: Optional[List[str]] = None,
                 use_cloudscraper: bool = True,
                 verbose: bool = True) -> Dict[str, List[str]]:

    platforms = platforms or list(PLATFORMS.keys())
    engines_priority = engines_priority or ["bing", "ddg_html", "startpage"]
    proxies_list = proxies or []
    proxy_idx = 0

    def get_next_client() -> HttpClient:
        nonlocal proxy_idx
        proxy = None
        if proxies_list:
            proxy = proxies_list[proxy_idx % len(proxies_list)]
            proxy_idx += 1
        if tor:
            proxy = proxy or "socks5://127.0.0.1:9050"
        client = HttpClient(proxy=proxy, use_cloudscraper=use_cloudscraper)
        return client

    # pre-generate query variations
    variations = generate_query_variations(name_or_username, extras_for_variations)
    if verbose:
        print(f"[i] Generated {len(variations)} query variations (extras={extras_for_variations})")
        print(f"[i] Engines priority: {engines_priority}")
        if proxies_list:
            print(f"[i] Using {len(proxies_list)} proxies (rotation enabled).")
        if tor:
            print(f"[i] Tor mode: enabled (socks5://127.0.0.1:9050)")

    all_results: Dict[str, List[str]] = {p: [] for p in platforms}
    # initial client
    client = get_next_client()

    for platform in platforms:
        collected: List[str] = []
        if verbose:
            print(f"\n🔎 جارٍ البحث في {platform.upper()} ...")
        for q in variations:
            if len(collected) >= results_per_platform:
                break
            q_full = quote_plus(q + f" site:{platform}.com")
            # try engines in order
            for eng in engines_priority:
                # rotate proxies by creating new client if proxies list present
                client = get_next_client() if proxies_list else client
                try:
                    found = engine_request_and_parse(eng, q_full, platform, client, results_per_platform, verbose=verbose)
                except Exception as e:
                    if verbose:
                        print(f"[!] Exception engine {eng}: {e}")
                    found = []
                # filter and collect
                if found:
                    filtered = filter_platform_urls(found, PLATFORMS[platform])
                    for u in filtered:
                        if u not in collected:
                            collected.append(u)
                # short jitter
                jitter_sleep(0.4, 1.0)
                if len(collected) >= results_per_platform:
                    break
            # small delay before next variation
            jitter_sleep()
        # final filter/dedupe and keep top-N
        collected = dedupe_keep_order(collected)[:results_per_platform]
        all_results[platform] = collected
        # print results per platform
        if verbose:
            if collected:
                for u in collected:
                    print("👉", u)
            else:
                print("❌ لا توجد نتائج.")
        # pause between platforms longer
        jitter_sleep(1.2, 3.0)

    return all_results

# ---------------- Save functions ----------------
def save_results(all_results: Dict[str, List[str]], base_filename: str = "results"):
    txt_file = base_filename + ".txt"
    csv_file = base_filename + ".csv"
    json_file = base_filename + ".json"

    with open(txt_file, "w", encoding="utf-8") as f:
        for p, links in all_results.items():
            f.write(f"=== {p.upper()} ===\n")
            if not links:
                f.write("NO RESULTS\n\n")
            else:
                for l in links:
                    f.write(l + "\n")
                f.write("\n")

    rows = []
    for p, links in all_results.items():
        if not links:
            rows.append([p, ""])
        else:
            for l in links:
                rows.append([p, l])
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["platform", "url"])
        w.writerows(rows)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ النتائج حفظت: {txt_file}, {csv_file}, {json_file}")

# ---------------- CLI / Main ----------------
def load_proxies_from_file(path: str) -> List[str]:
    if not path or not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out

def main():
    parser = argparse.ArgumentParser(description="OSINT multi-engine scraper (interactive)")
    parser.add_argument("query", nargs="*", help="الاسم أو اسم المستخدم (يمكن وضع بين \" \")")
    parser.add_argument("--results", "-r", type=int, default=DEFAULT_RESULTS_PER_PLATFORM, help="عدد الروابط لكل منصة (افتراضي 10)")
    parser.add_argument("--proxies-file", "-P", help="ملف يحتوي على بروكسيات (كل سطر proxy)")
    parser.add_argument("--proxy", help="استعمال بروكسي واحد مباشر (eg: http://IP:PORT or socks5://127.0.0.1:9050)")
    parser.add_argument("--tor", action="store_true", help="استعمال Tor SOCKS5 (127.0.0.1:9050)")
    parser.add_argument("--engines", "-e", nargs="+", default=["bing","ddg_html","startpage"], help="ترتيب المحركات")
    parser.add_argument("--extras", "-x", nargs="+", help="كلمات اضافية لاستخدامها في permutations (مثل: algeria instagram)")
    parser.add_argument("--no-cloudscraper", action="store_true", help="عدم استخدام cloudscraper حتى لو كان مثبت")
    parser.add_argument("--out", "-o", default="results", help="الاسم الأساسي لملفات الإخراج")
    parser.add_argument("--verbose", "-v", action="store_true", help="طباعة مفصلة أثناء التنفيذ")
    args = parser.parse_args()

    query = " ".join(args.query).strip() if args.query else ""
    if not query:
        query = input("[?] أدخل اسم المستخدم أو الاسم الكامل: ").strip()
    if not query:
        print("لا يوجد استعلام. الخروج.")
        sys.exit(1)

    proxies = []
    if args.proxy:
        proxies.append(args.proxy)
    if args.proxies_file:
        proxies += load_proxies_from_file(args.proxies_file)
    envp = os.environ.get("PROXIES")
    if envp:
        proxies += [p.strip() for p in envp.split(",") if p.strip()]

    use_cloud = HAS_CLOUDSCRAPER and not args.no_cloudscraper

    try:
        results = osint_search(
            name_or_username=query,
            platforms=None,
            results_per_platform=args.results,
            engines_priority=args.engines,
            proxies=proxies if proxies else None,
            tor=args.tor,
            extras_for_variations=args.extras,
            use_cloudscraper=use_cloud,
            verbose=args.verbose
        )
        save_results(results, args.out)
    except Exception as e:
        print("خطأ أثناء التنفيذ:", e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
