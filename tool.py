#!/usr/bin/env python3
# osint_tool_full.py
# Robust multi-engine OSINT scraper (Bing + DuckDuckGo + Startpage)
# Features: UA rotation, proxy rotation, Tor support, permutations, retries, backoff, save to txt/csv/json
# Platforms supported out-of-the-box: youtube, tiktok, reddit, linkedin, facebook, instagram
# Optional: add more platforms/domains in PLATFORMS dict.

import os
import sys
import time
import random
import json
import csv
import argparse
import traceback
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote, quote_plus

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except Exception:
    import requests
    HAS_CLOUDSCRAPER = False

from bs4 import BeautifulSoup

# ------------------- CONFIG -------------------
PLATFORMS = {
    "youtube": ["youtube.com", "youtu.be"],
    "tiktok": ["tiktok.com"],
    "reddit": ["reddit.com"],
    "linkedin": ["linkedin.com"],
    "facebook": ["facebook.com", "fb.com"],
    "instagram": ["instagram.com"]
}

DEFAULT_RESULTS_PER_PLATFORM = 5
DEFAULT_MIN_DELAY = 1.2
DEFAULT_MAX_DELAY = 3.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.5

# User agents rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
]

# Engines config: each engine: (base_url_format, parser_function_name)
# base_url_format should contain one {} for the query string (already encoded).
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

# ------------------------------------------------

# Session abstraction - uses cloudscraper if available else requests
class HttpClient:
    def __init__(self, proxy: Optional[str] = None, use_cloudscraper: bool = HAS_CLOUDSCRAPER):
        self.use_cloudscraper = use_cloudscraper and HAS_CLOUDSCRAPER
        if self.use_cloudscraper:
            try:
                self.s = cloudscraper.create_scraper()
            except Exception:
                self.s = None
                self.use_cloudscraper = False
        if not self.use_cloudscraper:
            import requests
            self.s = requests.Session()
        if proxy:
            # proxy may be like http://IP:PORT or socks5://127.0.0.1:9050 (requires requests[socks])
            self.s.proxies.update({"http": proxy, "https": proxy})

    def get(self, url, headers=None, timeout=15):
        return self.s.get(url, headers=headers, timeout=timeout)

# Utility helpers
def choose_ua():
    return random.choice(USER_AGENTS)

def jitter_sleep(min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY):
    time.sleep(random.uniform(min_delay, max_delay))

def normalize_url(u: str) -> str:
    # basic normalization: strip whitespace and unquote
    try:
        u = u.strip()
        # if it's a duckduckgo proxy link like //duckduckgo.com/l/?uddg=... handle elsewhere
        return unquote(u)
    except Exception:
        return u

def dedupe_keep_order(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def ensure_scheme(u: str) -> str:
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return "https://" + u

# ---------------- PARSERS ----------------
def parse_bing(html: str, platform_domains: List[str], limit: int) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Attempt patterns: li.b_algo h2 > a  (english) OR h2 > a (some locales)
    for sel in ["li.b_algo h2 a", "h2 a"]:
        for a in soup.select(sel):
            href = a.get("href")
            if not href:
                continue
            href = ensure_scheme(href)
            for domain in platform_domains:
                if domain in href:
                    results.append(normalize_url(href))
                    break
            if len(results) >= limit:
                break
        if results:
            break

    # fallback: check anchor tags inside result blocks
    if not results:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href:
                continue
            for domain in platform_domains:
                if domain in href:
                    results.append(normalize_url(href))
            if len(results) >= limit:
                break

    return dedupe_keep_order(results)[:limit]

def parse_ddg_html(html: str, platform_domains: List[str], limit: int) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    # DuckDuckGo HTML has anchors with class result__a whose href contains 'uddg=' parameter sometimes
    for a in soup.select("a.result__a, a.result__snippet, a.result__url, a[href]"):
        href = a.get("href")
        if not href:
            continue
        # If it's a redirect style with uddg param
        if "uddg=" in href:
            try:
                parsed = parse_qs(urlparse(href).query)
                if "uddg" in parsed:
                    real = parsed["uddg"][0]
                    real = ensure_scheme(unquote(real))
                    for d in platform_domains:
                        if d in real:
                            results.append(normalize_url(real))
                            break
            except Exception:
                pass
        else:
            href_full = ensure_scheme(href)
            for d in platform_domains:
                if d in href_full:
                    results.append(normalize_url(href_full))
                    break
        if len(results) >= limit:
            break
    return dedupe_keep_order(results)[:limit]

def parse_startpage(html: str, platform_domains: List[str], limit: int) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    # Startpage sometimes wraps links in a tags with class w-gl__result-title or with a direct href
    for sel in ["a.w-gl__result-title", "a.result-url", "a[href]"]:
        for a in soup.select(sel):
            href = a.get("href")
            if not href:
                continue
            href = ensure_scheme(href)
            for d in platform_domains:
                if d in href:
                    results.append(normalize_url(href))
                    break
            if len(results) >= limit:
                break
        if results:
            break
    return dedupe_keep_order(results)[:limit]

# --------------- SEARCH ENGINE CALL ---------------
def engine_request_and_parse(engine_key: str, query_encoded: str, platform: str, client: HttpClient, results_limit: int, timeout=15) -> List[str]:
    engine = ENGINES.get(engine_key)
    if not engine:
        return []
    url = engine["url"].format(query_encoded)
    headers = {
        "User-Agent": choose_ua(),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.bing.com/"
    }

    # Try with exponential backoff
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
                # if blocked or 202 or others, raise to retry with jitter/backoff
                last_exc = Exception(f"HTTP {status} from {engine_key}")
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
            time.sleep(backoff + random.random())
            backoff *= DEFAULT_BACKOFF_FACTOR
            continue
    # after attempts
    if last_exc:
        # print minimal debug info
        print(f"[!] Engine {engine_key} failed after {DEFAULT_MAX_RETRIES} attempts: {last_exc}")
    return []

# ---------------- Permutations generator ----------------
def generate_query_variations(name: str, extras: Optional[List[str]] = None) -> List[str]:
    """
    Generate reasonable permutations:
    - original
    - tokens permutations
    - with extras appended (country, instagram)
    - quoted versions
    """
    name = name.strip()
    tokens = [t for t in name.split() if t]
    variations = []
    if not tokens:
        return variations
    # original and quoted
    variations.append(name)
    variations.append('"' + name + '"')
    # simple permutations of tokens (up to 3 tokens permute)
    if len(tokens) > 1:
        from itertools import permutations
        perms = set()
        for r in range(1, min(4, len(tokens)+1)):
            for p in permutations(tokens, r):
                perms.add(" ".join(p))
        for p in perms:
            variations.append(p)
            variations.append('"' + p + '"')
    # add extras
    extras = extras or []
    extras = [e for e in extras if e]
    for base in list(variations):
        for ex in extras:
            variations.append(f"{base} {ex}")
    # dedupe while keeping order
    seen = set(); out = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out[:60]  # cap

# ---------------- Core tool function ----------------
def osint_search(name_or_username: str,
                 platforms: Optional[List[str]] = None,
                 results_per_platform: int = DEFAULT_RESULTS_PER_PLATFORM,
                 engines_priority: Optional[List[str]] = None,
                 proxies: Optional[List[str]] = None,
                 tor: bool = False,
                 extras_for_variations: Optional[List[str]] = None,
                 verbose: bool = True) -> Dict[str, List[str]]:

    platforms = platforms or list(PLATFORMS.keys())
    engines_priority = engines_priority or ["bing", "ddg_html", "startpage"]

    # prepare proxies rotation
    proxies_list = proxies or []
    proxy_idx = 0

    all_results: Dict[str, List[str]] = {p: [] for p in platforms}

    # create initial client (no proxy or first proxy)
    def get_next_client() -> HttpClient:
        nonlocal proxy_idx
        proxy = None
        if proxies_list:
            proxy = proxies_list[proxy_idx % len(proxies_list)]
            proxy_idx += 1
        # if tor requested, override proxy to socks5 localhost
        if tor:
            proxy = proxy or "socks5://127.0.0.1:9050"
        client = HttpClient(proxy=proxy, use_cloudscraper=True)
        return client

    client = get_next_client()

    # generate query variations once
    variations = generate_query_variations(name_or_username, extras_for_variations)

    if verbose:
        print(f"[i] Generated {len(variations)} query variations (using extras={extras_for_variations})")
        print(f"[i] Engines priority: {engines_priority}")
        if proxies_list:
            print(f"[i] Using {len(proxies_list)} proxies (rotation enabled).")
        if tor:
            print(f"[i] Tor mode: enabled (socks5://127.0.0.1:9050)")

    for platform in platforms:
        collected = []
        if verbose:
            print("\n🔎 البحث في", platform.upper(), "...")
        # For each variation try engines in priority until we have enough results
        for q in variations:
            if len(collected) >= results_per_platform:
                break
            q_encoded = quote_plus(q + f" site:{platform}.com")
            # try engines in order
            engine_success = False
            for eng in engines_priority:
                # rotate client every engine call optionally to avoid persistent blocking
                client = get_next_client() if proxies_list else client
                try:
                    found = engine_request_and_parse(eng, q_encoded, platform, client, results_per_platform)
                except Exception as e:
                    if verbose:
                        print(f"[!] Exception while calling engine {eng}: {e}")
                    found = []
                if found:
                    for f in found:
                        if f and f not in collected:
                            collected.append(f)
                    engine_success = True
                # short jitter between engine calls
                jitter_sleep(0.6, 1.2)
                if len(collected) >= results_per_platform:
                    break
            # if engines returned something for this query, continue with next platform's query (or keep trying variations)
            # small delay between queries
            jitter_sleep()
        # final dedupe and keep limit
        collected = dedupe_keep_order(collected)[:results_per_platform]
        all_results[platform] = collected
        if verbose:
            if collected:
                for u in collected:
                    print("👉", u)
            else:
                print("❌ لا توجد نتائج.")
        # pause between platforms longer
        jitter_sleep(1.5, 3.5)

    return all_results

# -------------- Save helpers --------------
def save_results(all_results: Dict[str, List[str]], base_filename: str = "results"):
    txt_file = base_filename + ".txt"
    csv_file = base_filename + ".csv"
    json_file = base_filename + ".json"

    # txt
    with open(txt_file, "w", encoding="utf-8") as f:
        for p, links in all_results.items():
            f.write(f"=== {p.upper()} ===\n")
            if not links:
                f.write("NO RESULTS\n\n")
            else:
                for l in links:
                    f.write(l + "\n")
                f.write("\n")

    # csv
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

    # json
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ النتائج حفظت: {txt_file}, {csv_file}, {json_file}")

# ---------------- CLI ----------------
def load_proxies_from_file(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l and not l.startswith("#"):
                lines.append(l)
    return lines

def main():
    parser = argparse.ArgumentParser(description="OSINT multi-engine scraper")
    parser.add_argument("query", nargs="*", help="الاسم واللقب أو اسم المستخدم (يمكن اقتباسه)")
    parser.add_argument("--platforms", "-p", nargs="+", help="قائمة منصات (default: youtube tiktok reddit linkedin facebook instagram)")
    parser.add_argument("--results", "-r", type=int, default=DEFAULT_RESULTS_PER_PLATFORM, help="عدد النتائج لكل منصة")
    parser.add_argument("--proxies-file", "-P", help="ملف البروكسيات (كل سطر proxy like http://IP:PORT or socks5://127.0.0.1:9050)")
    parser.add_argument("--proxy", help="استخدم proxy واحد مباشرة")
    parser.add_argument("--tor", action="store_true", help="استخدم Tor (socks5://127.0.0.1:9050)")
    parser.add_argument("--engines", "-e", nargs="+", default=["bing","ddg_html","startpage"], help="engines order")
    parser.add_argument("--extras", "-x", nargs="+", help="كلمات لإضافتها للـ permutations (مثال: algeria instagram)")
    parser.add_argument("--no-cloudscraper", action="store_true", help="عدم استخدام cloudscraper حتى لو كان مثبت")
    parser.add_argument("--out", "-o", default="results", help="base filename to save outputs (txt,csv,json)")
    parser.add_argument("--verbose", "-v", action="store_true", help="طباعة مفصلة")
    args = parser.parse_args()

    query = " ".join(args.query) if args.query else None
    if not query:
        query = input("[?] أدخل الاسم واللقب أو اسم المستخدم: ").strip()
    if not query:
        print("لا يوجد استعلام. الخروج.")
        sys.exit(1)

    # setup proxies
    proxies = []
    if args.proxy:
        proxies = [args.proxy]
    if args.proxies_file:
        proxies += load_proxies_from_file(args.proxies_file)
    # also check env var PROXIES (comma separated)
    envp = os.environ.get("PROXIES")
    if envp:
        proxies += [p.strip() for p in envp.split(",") if p.strip()]

    use_cloud = HAS_CLOUDSCRAPER and not args.no_cloudscraper

    # run
    try:
        results = osint_search(
            name_or_username=query,
            platforms=args.platforms or None,
            results_per_platform=args.results,
            engines_priority=args.engines,
            proxies=proxies if proxies else None,
            tor=args.tor,
            extras_for_variations=args.extras,
            verbose=args.verbose
        )
        save_results(results, args.out)
    except Exception as e:
        print("خطأ عام أثناء التنفيذ:", e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
