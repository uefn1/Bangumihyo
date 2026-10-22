import os, sys
from datetime import datetime, timezone

def log(s): print(f"[download] {s}")

def fetch_cloudscraper(url):
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows'})
        r = scraper.get(url, timeout=30)
        log(f"cloudscraper {url} -> {r.status_code} len={len(r.text)}")
        if r.status_code==200 and len(r.text)>2000:
            return r.text
    except Exception as e:
        log(f"cloudscraper fail {e}")
    return None

def fetch_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0", locale="es-PY")
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(7000)  # mi.tvはJS描画に時間がかかる
            html = page.content()
            browser.close()
            log(f"playwright {url} len={len(html)}")
            return html if len(html)>2000 else None
    except Exception as e:
        log(f"playwright fail {e}")
        return None

def download_and_save(name, url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    html = fetch_cloudscraper(url)
    if not html:
        log(f"{name} cloudscraper failed, trying playwright")
        html = fetch_playwright(url)
    
    if html:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        log(f"{name} saved -> {path} ({len(html)} bytes)")
        return True
    else:
        log(f"{name} BOTH FAILED - keeping old file if exists")
        return False

# 3ソースをダウンロード
download_and_save("mi.tv", "https://mi.tv/py/canales/tigo-sports", "docs/raw/mi_tv.html")
download_and_save("APF", "https://www.apf.org.py", "docs/raw/apf.html")
download_and_save("Versus", "https://www.versus.com.py", "docs/raw/versus.html")
