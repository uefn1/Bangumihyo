import requests, json, re, os
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def to_jst(t):
    try:
        h,m = map(int, t.split(":"))
        return f"{(h+13)%24:02d}:{m:02d}"
    except: return t

def scrape_mi_tv():
    url = "https://mi.tv/py/canales/tigo-sports"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
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

def scrape_apf():
    url = "https://www.apf.org.py"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        progs=[]
        # APFは記事タイトルに「20:30 horas ... Tigo Sports」と書かれる
        for a in soup.find_all("a"):
            txt = a.get_text(" ", strip=True)
            if "Tigo Sports" in txt and re.search(r"\d{1,2}:\d{2}", txt):
                m = re.search(r"(\d{1,2}:\d{2})", txt)
                if m:
                    time = m.group(1)
                    # ゼロ埋め
                    h,mn = time.split(":")
                    time = f"{int(h):02d}:{mn}"
                    progs.append({
                        "time_py": time,
                        "time_jst": to_jst(time),
                        "title": txt[:120],
                        "category": "Fútbol - APF"
                    })
        # 重複除去
        uniq = {p["title"]:p for p in progs}.values()
        progs = list(uniq)[:20]
        return {"status":"ok","url":url,"count":len(progs),"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":progs}
    except Exception as e:
        return {"status":"error","url":url,"error":str(e),"count":0,"programs":[]}

def scrape_versus():
    url = "https://www.versus.com.py"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        progs=[]
        for el in soup.find_all(string=re.compile("Tigo Sports")):
            parent = el.parent.get_text(" ", strip=True) if el.parent else str(el)
            if len(parent) < 200:
                m = re.search(r"(\d{1,2}:\d{2})", parent)
                time = m.group(1) if m else "--:--"
                if ":" in time:
                    h,mn = time.split(":")
                    time = f"{int(h):02d}:{mn}"
                progs.append({
                    "time_py": time,
                    "time_jst": to_jst(time) if time!="--:--" else "--:--",
                    "title": parent[:120],
                    "category": "Agenda Versus"
                })
        uniq = {p["title"]:p for p in progs}.values()
        progs = list(uniq)[:20]
        return {"status":"ok","url":url,"count":len(progs),"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":progs}
    except Exception as e:
        return {"status":"error","url":url,"error":str(e),"count":0,"programs":[]}

sources = {
    "mi.tv": scrape_mi_tv(),
    "APF Oficial": scrape_apf(),
    "Versus": scrape_versus()
}

os.makedirs("docs", exist_ok=True)
with open("docs/data.json","w",encoding="utf-8") as f:
    json.dump({"generated_at_utc":datetime.now(timezone.utc).isoformat(),"sources":sources}, f, ensure_ascii=False, indent=2)

print(f"mi.tv={sources['mi.tv']['count']} APF={sources['APF Oficial']['count']} Versus={sources['Versus']['count']}")
