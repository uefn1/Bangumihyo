import requests, json, re, os, sys
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def to_jst(t):
    try:
        t = t.strip()
        m = re.match(r"(\d{1,2}):(\d{2})", t)
        if not m: return t
        h = int(m.group(1))
        return f"{(h+13)%24:02d}:{m.group(2)}"
    except:
        return t

def log(msg):
    print(f"[scrape] {msg}", file=sys.stderr)

def scrape_mi_tv():
    url = "https://mi.tv/py/canales/tigo-sports"
    try:
        r = requests.get(url, headers={
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language":"es-PY,es;q=0.9"
        }, timeout=20)
        r.raise_for_status()
        log(f"mi.tv status={r.status_code} len={len(r.text)}")
        soup = BeautifulSoup(r.text, "lxml")
        
        # 方法1: テキストを行ごとに見る - 最も安定
        text = soup.get_text("\n")
        lines = [re.sub(r"^#+\s*", "", l).strip() for l in text.splitlines()]
        lines = [l for l in lines if l]

        progs=[]
        for i, line in enumerate(lines):
            # 05:00 のような時刻行
            tm = re.match(r"^(\d{2}:\d{2})$", line)
            if tm:
                time = tm.group(1)
                # 次の1-2行がタイトルのはず
                if i+1 < len(lines):
                    title = lines[i+1]
                    # 時刻や「Mostrar」などのUI文言は除外
                    if re.match(r"^\d{2}:\d{2}$", title): continue
                    if "Mostrar" in title or "Esconder" in title: continue
                    if len(title) < 3: continue
                    # 説明はさらに次
                    desc = lines[i+2] if i+2 < len(lines) and len(lines[i+2])>10 else ""
                    progs.append({
                        "time_py": time,
                        "time_jst": to_jst(time),
                        "title": title[:120],
                        "description": desc[:200],
                        "category": "Fútbol" if "vs." in title or "vs" in title.lower() else "Noticias" if "Noticias" in title else "Programas"
                    })
        
        # 方法2: 1行に「05:00 De taquito」のようにまとまっている場合のフォールバック
        if len(progs) < 3:
            log("mi.tv fallback regex")
            for m in re.finditer(r"(\d{2}:\d{2})\s+([A-Za-zÁÉÍÓÚÑáéíóúñ0-9\.\s\-!¡]+?)(?:\n|$)", text):
                time, title = m.groups()
                title = title.strip()
                if len(title) < 3: continue
                if "Programación" in title: continue
                progs.append({
                    "time_py": time,
                    "time_jst": to_jst(time),
                    "title": title[:120],
                    "category": "Programas"
                })

        # 重複除去
        seen={}
        for p in progs:
            key = p["time_py"]+"|"+p["title"].lower()
            seen[key]=p
        progs = sorted(seen.values(), key=lambda x: x["time_py"])

        log(f"mi.tv parsed {len(progs)} programs")
        return {"status":"ok" if progs else "empty","url":url,"count":len(progs),"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":progs}
    except Exception as e:
        log(f"mi.tv error {e}")
        return {"status":"error","url":url,"error":str(e),"count":0,"programs":[]}

def scrape_apf():
    url = "https://www.apf.org.py"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        progs=[]
        # APFは記事内に「19:00 horas ... 【entity-Tigo Sports¦canonical_name=Tigo Sports】」のパターン
        for txt in soup.stripped_strings:
            if "【entity-Tigo Sports¦canonical_name=Tigo Sports】" in txt:
                # 同じ文字列内に時刻があるか
                m = re.search(r"(\d{1,2}:\d{2})", txt)
                if m:
                    time_raw = m.group(1)
                    h,mm = time_raw.split(":")
                    time = f"{int(h):02d}:{mm}"
                    progs.append({
                        "time_py": time,
                        "time_jst": to_jst(time),
                        "title": txt[:140],
                        "category": "APF - Fútbol"
                    })
        # もっと広く全文から「a las 20:30 horas ... 【entity-Tigo Sports¦canonical_name=Tigo Sports】」を拾う
        full = soup.get_text(" ", strip=True)
        for m in re.finditer(r"a las (\d{1,2}:\d{2})[^.]{0,120}【entity-Tigo Sports¦canonical_name=Tigo Sports】", full, re.IGNORECASE):
            time_raw = m.group(1)
            h,mm = time_raw.split(":")
            time = f"{int(h):02d}:{mm}"
            snippet = m.group(0)[:140]
            progs.append({
                "time_py": time,
                "time_jst": to_jst(time),
                "title": snippet,
                "category": "APF - Fútbol"
            })

        uniq={p["title"]:p for p in progs}
        progs=list(uniq.values())[:20]
        log(f"APF parsed {len(progs)}")
        return {"status":"ok" if progs else "empty","url":url,"count":len(progs),"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":progs}
    except Exception as e:
        log(f"APF error {e}")
        return {"status":"error","url":url,"error":str(e),"count":0,"programs":[]}

def scrape_versus():
    url = "https://www.versus.com.py"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        progs=[]
        full = soup.get_text(" ", strip=True)
        # Versusは「TV: En directo por 【entity-Tigo Sports¦canonical_name=Tigo Sports】」表記
        for m in re.finditer(r"([^.]{0,80}【entity-Tigo Sports¦canonical_name=Tigo Sports】[^.]{0,20})", full, re.IGNORECASE):
            txt = m.group(1).strip()
            tm = re.search(r"(\d{1,2}:\d{2})", txt)
            time = f"{int(tm.group(1).split(':')[0]):02d}:{tm.group(1).split(':')[1]}" if tm else "--:--"
            progs.append({
                "time_py": time,
                "time_jst": to_jst(time) if time!="--:--" else "--:--",
                "title": txt[:140],
                "category": "Versus"
            })
        uniq={p["title"]:p for p in progs}
        progs=list(uniq.values())[:20]
        log(f"Versus parsed {len(progs)}")
        return {"status":"ok" if progs else "empty","url":url,"count":len(progs),"fetched_at":datetime.now(timezone.utc).isoformat(),"programs":progs}
    except Exception as e:
        log(f"Versus error {e}")
        return {"status":"error","url":url,"error":str(e),"count":0,"programs":[]}

# 実行
sources = {
    "mi.tv": scrape_mi_tv(),
    "APF Oficial": scrape_apf(),
    "Versus": scrape_versus()
}

# 重要: 取得数が0の時は古いdata.jsonを保持して上書きしない
old_path = "docs/data.json"
old_data = {}
if os.path.exists(old_path):
    try:
        with open(old_path,"r",encoding="utf-8") as f:
            old_data = json.load(f)
    except: pass

for key in list(sources.keys()):
    if sources[key]["count"] == 0:
        # 古いデータがあればそちらを維持
        if old_data.get("sources",{}).get(key,{}).get("programs"):
            log(f"{key} empty -> keeping old {len(old_data['sources'][key]['programs'])} programs")
            sources[key] = old_data["sources"][key]
            sources[key]["status"] = "kept_old"

os.makedirs("docs", exist_ok=True)
with open(old_path,"w",encoding="utf-8") as f:
    json.dump({"generated_at_utc":datetime.now(timezone.utc).isoformat(),"sources":sources}, f, ensure_ascii=False, indent=2)

for k,v in sources.items():
    print(f"{k}: {v['count']} status={v['status']}")
