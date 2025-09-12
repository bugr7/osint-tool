import requests
import os
import time
from bs4 import BeautifulSoup
import urllib.parse
import re

SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:5000")

def post_log(data):
    try:
        requests.post(f"{SERVER_URL}/log_search", json=data, timeout=10)
    except:
        pass

def duckduckgo_search_links(query, site=None, num_results=10):
    search_query = f"{query} site:{site}" if site else query
    url = "https://html.duckduckgo.com/html/"
    params = {"q": search_query}
    links = []
    for attempt in range(5):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                anchors = soup.select("a.result__a") or soup.find_all("a")
                for a in anchors:
                    href = a.get("href")
                    if href:
                        link = None
                        if "uddg=" in href:
                            m = re.search(r"uddg=([^&]+)", href)
                            if m:
                                link = urllib.parse.unquote(m.group(1))
                        else:
                            link = href
                        if link and link.startswith("http") and "duckduckgo.com" not in link and link not in links:
                            links.append(link)
                        if len(links) >= num_results:
                            break
                if links:
                    return links
            elif resp.status_code == 202:
                wait = 3 * (attempt + 1)
                time.sleep(wait)
                continue
        except:
            time.sleep(2)
    return links
