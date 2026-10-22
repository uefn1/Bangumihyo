import requests, json, re, os
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def to_jst(t):
    try:
        h,m = map(int, t.split(":"))
        return f"{(h+13)%24:02d}:{m:02d}"
    except:
        return t

def scrape_mi_tv():
    url = "https://mi.tv/py/canales/tigo-sports"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        progs=[]
        for m in re.finditer(r"-\s*(\d{2}:\d{2})\s*\n+##\s*(.+)", soup.get_text()):
            time,title = m.groups()
            progs.append({
                "time_py": time.strip(),
                "time_jst": to_jst(time.strip()),
                "title": title.strip()[:120],
                "category": "Fútbol" if "vs." in title else "Noticias" if "Noticias" in title else "Programas"
            })
        return {"status":"ok","url":url,"count":len(progs),"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":progs}
    except Exception as e:
        return {"status":"error","url":url,"error":str(e),"count":0,"programs":[]}

def scrape_television():
    url = "https://television.com.py/tigo-sports-en-vivo"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_timeout(8000)
            text = page.content()
            b.close()
        soup = BeautifulSoup(text, "lxml")
        progs=[]
        for line in soup.get_text("\n").splitlines():
            m = re.match(r"(\d{2}:\d{2})\s+(.+)", line.strip())
            if m:
                time,title = m.groups()
                progs.append({"time_py":time,"time_jst":to_jst(time),"title":title[:120],"category":"Programas"})
        return {"status":"ok","url":url,"count":len(progs),"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":progs}
    except Exception as e:
        return {"status":"error","url":url,"error":str(e),"count":0,"programs":[]}

def scrape_official():
    url = "https://www.tigosports.com.py/"
    return {"status":"ok","url":url,"count":0,"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":[],"note":"login required - placeholder"}

sources = {
    "mi.tv": scrape_mi_tv(),
    "television.com.py": scrape_television(),
    "tigosports.com.py": scrape_official()
}

os.makedirs("docs", exist_ok=True)
with open("docs/data.json","w",encoding="utf-8") as f:
    json.dump({"generated_at_utc":datetime.now(timezone.utc).isoformat(),"sources":sources}, f, ensure_ascii=False, indent=2)
