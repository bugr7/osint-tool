import requests
from bs4 import BeautifulSoup

def test_bing(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://www.bing.com/search?q={query}"
    response = requests.get(url, headers=headers, timeout=10)

    print("🔎 HTTP Status:", response.status_code)
    print("🌐 Bing URL:", response.url)
    print("\n📄 أول 2000 حرف من HTML:\n")
    print(response.text[:2000])  # نعرض أول 2000 كاراكتر من الصفحة

test_bing("elon musk site:youtube.com")
