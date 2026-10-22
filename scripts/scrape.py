import json, re, os, sys
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def to_jst(t):
    try:
        h,m = map(int, re.match(r"(\d{1,2}):(\d{2})", t).groups())
        return f"{(h+13)%24:02d}:{m:02d}"
    except: return t

def log(s): print(f"[parse] {s}")

def parse_mi_tv_from_file(path):
    if not os.path.exists(path):
        log(f"mi.tv file not found {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        html=f.read()
    log(f"mi.tv file len={len(html)}")
    soup=BeautifulSoup(html, "lxml")
    lines=[re.sub(r"^#+\s*","",l).strip() for l in soup.get_text("\n").splitlines() if l.strip()]
    log(f"mi.tv lines sample {lines[:15]}")
    progs=[]
    for i, line in enumerate(lines):
        if re.fullmatch(r"\d{2}:\d{2}", line):
            if i+1 < len(lines):
                title=lines[i+1]
                if len(title)<3 or "Mostrar" in title: continue
                progs.append({"time_py":line,"time_jst":to_jst(line),"title":title[:120],"category":"Fútbol" if "vs" in title.lower() else "Programas"})
    # 重複除去
    uniq={p["time_py"]+"|"+p["title"]:p for p in progs}
    return sorted(uniq.values(), key=lambda x: x["time_py"])

def parse_generic_from_file(path, keyword="Tigo Sports"):
    if not os.path.exists(path): return []
    with open(path,"r",encoding="utf-8") as f:
        html=f.read()
    soup=BeautifulSoup(html,"lxml")
    full=soup.get_text(" ", strip=True)
    progs=[]
    for m in re.finditer(r"(\d{1,2}:\d{2})[^.]{0,150}"+keyword, full, re.I):
        raw=m.group(0)[:140]
        tm=m.group(1)
        h,mm=tm.split(":")
        time=f"{int(h):02d}:{mm}"
        progs.append({"time_py":time,"time_jst":to_jst(time),"title":raw,"category":"Fútbol"})
    uniq={p["title"]:p for p in progs}
    return list(uniq.values())[:20]

os.makedirs("docs", exist_ok=True)
sources={
    "mi.tv": {"url":"https://mi.tv/py/canales/tigo-sports","programs": parse_mi_tv_from_file("docs/raw/mi_tv.html")},
    "APF Oficial": {"url":"https://www.apf.org.py","programs": parse_generic_from_file("docs/raw/apf.html")},
    "Versus": {"url":"https://www.versus.com.py","programs": parse_generic_from_file("docs/raw/versus.html")}
}

for k in sources:
    progs=sources[k]["programs"]
    sources[k].update({
        "status":"ok" if progs else "empty",
        "count": len(progs),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    })
    log(f"{k}: {len(progs)}")

with open("docs/data.json","w",encoding="utf-8") as f:
    json.dump({"generated_at_utc":datetime.now(timezone.utc).isoformat(),"sources":sources}, f, ensure_ascii=False, indent=2)
