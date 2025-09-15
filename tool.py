# osint_tool_final.py
import requests
import json
import csv
import time
from urllib.parse import quote

# ===== إعدادات المنصات =====
PLATFORMS = {
    "YOUTUBE": "site:youtube.com",
    "TIKTOK": "site:tiktok.com",
    "REDDIT": "site:reddit.com",
    "LINKEDIN": "site:linkedin.com",
    "FACEBOOK": "site:facebook.com",
    "INSTAGRAM": "site:instagram.com"
}

# ===== دوال البحث =====
def search_bing(query, limit=10):
    """بحث في Bing"""
    url = f"https://www.bing.com/search?q={quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            links = [line.split('"')[0] for line in r.text.split("href=\"")[1:]]
            for link in links:
                if link.startswith("http") and not link.startswith("https://go.microsoft.com"):
                    results.append(link)
                if len(results) >= limit:
                    break
    except Exception as e:
        print(f"[!] خطأ في Bing: {e}")
    return results

def search_duckduckgo(query, limit=10):
    """بحث في DuckDuckGo"""
    url = f"https://duckduckgo.com/html/?q={quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            links = [line.split('"')[0] for line in r.text.split("uddg=")[1:]]
            for link in links:
                if link.startswith("http"):
                    results.append(link)
                if len(results) >= limit:
                    break
    except Exception as e:
        print(f"[!] خطأ في DuckDuckGo: {e}")
    return results

def clean_links(links, domain):
    """فلترة الروابط لتخص المنصة فقط"""
    return [l for l in links if domain in l]

# ===== البرنامج الرئيسي =====
def main():
    query = input("[?] أدخل اسم المستخدم أو الاسم الكامل: ").strip()
    all_results = {}

    for platform, site in PLATFORMS.items():
        print(f"\n🔎 جارٍ البحث في {platform} ...")
        q = f"{query} {site}"

        # جرب Bing أولاً
        results = search_bing(q, limit=15)

        # لو فارغة جرب DuckDuckGo
        if not results:
            results = search_duckduckgo(q, limit=15)

        # فلترة الروابط
        results = clean_links(results, site.replace("site:", ""))[:10]

        if results:
            for link in results:
                print(f"👉 {link}")
        else:
            print("❌ لا توجد نتائج.")

        all_results[platform] = results

        time.sleep(2)  # تأخير بسيط لتفادي البلوك

    # ===== حفظ النتائج =====
    with open("results.txt", "w", encoding="utf-8") as f:
        for platform, links in all_results.items():
            f.write(f"\n{platform}:\n")
            for link in links:
                f.write(link + "\n")

    with open("results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Platform", "Link"])
        for platform, links in all_results.items():
            for link in links:
                writer.writerow([platform, link])

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

    print("\n✅ النتائج حفظت في results.txt و results.csv و results.json")

if __name__ == "__main__":
    main()
