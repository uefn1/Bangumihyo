import json, re, os, sys, time
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def to_jst(t):
    try:
        h,m = map(int, re.match(r"(\d{1,2}):(\d{2})", t.strip()).groups())
        return f"{(h+13)%24:02d}:{m:02d}"
    except:
        return t

def log(s):
    print(f"[scrape] {s}")

def fetch_with_cloudscraper(url):
    """requestsの代わりにcloudscraperを使う"""
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={'browser':'chrome','platform':'windows','mobile':False}
        )
        r = scraper.get(url, timeout=25)
        log(f"cloudscraper {url} -> {r.status_code} len={len(r.text)}")
        if r.status_code == 200 and len(r.text) > 1000:
            return r.text
    except Exception as e:
        log(f"cloudscraper fail {e}")
    return None

def fetch_with_playwright(url):
    """最終手段: 本物のブラウザで取得"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Paraguayのロケールっぽく見せる
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                locale="es-PY"
            )
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
            # mi.tvはJSで数秒後に描画される
            page.wait_for_timeout(6000)
            html = page.content()
            log(f"playwright {url} len={len(html)}")
            browser.close()
            return html if len(html) > 1000 else None
    except Exception as e:
        log(f"playwright fail {e}")
        return None

def get_html(url):
    # 1. cloudscraper -> 2. playwright の順で試す
    html = fetch_with_cloudscraper(url)
    if html:
        return html
    log(f"{url} cloudscraper failed, trying playwright")
    return fetch_with_playwright(url)

def parse_mi_tv(html):
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # デバッグ: 最初の20行をログに出す
    log(f"mi.tv first lines: {lines[:20]}")

    progs=[]
    # パターンA: 時刻行が単独
    for i, line in enumerate(lines):
        if re.fullmatch(r"\d{2}:\d{2}", line):
            if i+1 < len(lines):
                title = re.sub(r"^#+\s*", "", lines[i+1])
                if len(title) < 3: continue
                if "Mostrar" in title or "Esconder" in title: continue
                progs.append({
                    "time_py": line,
                    "time_jst": to_jst(line),
                    "title": title[:120],
                    "category": "Fútbol" if "vs" in title.lower() else "Programas"
                })
    # パターンB: 同じ行に時刻とタイトル
    if len(progs) < 3:
        for m in re.finditer(r"(\d{2}:\d{2})\s+([A-Za-zÁÉÍÓÚÑ0-9][^ \n]{2,})", text):
            time, title = m.groups()
            title = title.strip()
            if len(title) < 3: continue
            progs.append({"time_py": time, "time_jst": to_jst(time), "title": title[:120], "category":"Programas"})
    
    # 重複排除
    uniq={}
    for p in progs:
        uniq[p["time_py"]+"|"+p["title"]]=p
    return sorted(uniq.values(), key=lambda x: x["time_py"])

def parse_generic_tigo(html):
    if not html: return []
    progs=[]
    full = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    for m in re.finditer(r"(\d{1,2}:\d{2})[^.]{0,150}Tigo Sports", full, re.I):
        snippet = m.group(0)[:140]
        tm = m.group(1)
        h,mm = tm.split(":")
        time = f"{int(h):02d}:{mm}"
        progs.append({"time_py": time, "time_jst": to_jst(time), "title": snippet, "category":"Fútbol"})
    return progs[:20]

def scrape_source(name, url, parser):
    html = get_html(url)
    if not html:
        return {"status":"error","url":url,"error":"both fetch methods failed","count":0,"programs":[],"fetched_at":datetime.now(timezone.utc).isoformat()}
    progs = parser(html)
    status = "ok" if progs else "empty"
    log(f"{name} -> {len(progs)} programs status={status}")
    return {"status":status,"url":url,"count":len(progs),"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":progs}

sources = {
    "mi.tv": scrape_source("mi.tv", "https://mi.tv/py/canales/tigo-sports", parse_mi_tv),
    "APF Oficial": scrape_source("APF Oficial", "https://www.apf.org.py", parse_generic_tigo),
    "Versus": scrape_source("Versus", "https://www.versus.com.py", parse_generic_tigo),
}

# 0件なら古いデータを保持
old_path="docs/data.json"
if os.path.exists(old_path):
    try:
        with open(old_path,"r",encoding="utf-8") as f:
            old=json.load(f)
        for k in sources:
            if sources[k]["count"]==0 and old.get("sources",{}).get(k,{}).get("programs"):
                log(f"{k} keep old {len(old['sources'][k]['programs'])}")
                sources[k]=old["sources"][k]
                sources[k]["status"]="kept_old"
    except Exception as e:
        log(f"keep old fail {e}")

os.makedirs("docs", exist_ok=True)
with open(old_path,"w",encoding="utf-8") as f:
    json.dump({"generated_at_utc":datetime.now(timezone.utc).isoformat(),"sources":sources}, f, ensure_ascii=False, indent=2)

for k,v in sources.items():
    print(f"{k}: {v['count']} {v['status']}")
