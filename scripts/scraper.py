import requests, json, datetime, os, re
from bs4 import BeautifulSoup

BASE_URL = "https://mi.tv/py/canales/tigo-sports"
DAYS_TO_FETCH = 7

def fetch_mi_tv(date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    today = datetime.date.today()
    url = f"{BASE_URL}/{date_str}" if date_obj != today else BASE_URL
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-PY,es;q=0.9"
        }, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        
        programs = []
        # mi.tv の実際の構造から直接取る
        for li in soup.select("li"):
            txt = li.get_text(" ", strip=True)
            m = re.search(r'(\d{1,2}:\d{2})', txt)
            if not m:
                continue
            hora = m.group(1)
            titulo = txt.replace(hora, "").strip()
            # ノイズ除去
            if len(titulo) < 5 or len(titulo) > 150:
                continue
            if any(x in titulo.lower() for x in ['cookie', 'política', 'aceptar', 'mi.tv']):
                continue
            # 重複の「【entity-Tigo Sports¦canonical_name=Tigo Sports】 【entity-Tigo Sports¦canonical_name=Tigo Sports】」を除去
            titulo = re.sub(r'^(【entity-Tigo Sports¦canonical_name=Tigo Sports】\s*\+?\s*)+', '', titulo).strip()
            titulo = titulo[:120]
            
            programs.append({
                "hora_pyt": hora,
                "titulo": titulo,
                "canal": "【entity-Tigo Sports¦canonical_name=Tigo Sports】 + " if "【entity-Tigo Sports¦canonical_name=Tigo Sports】 +" in txt else "【entity-Tigo Sports¦canonical_name=Tigo Sports】",
                "categoria": "Primera División" if " vs " in titulo or " vs." in titulo else "Programa",
                "en_vivo": "vivo" in txt.lower()
            })
        
        # 重複除去 + ソート
        seen = set()
        uniq = []
        for p in sorted(programs, key=lambda x: x["hora_pyt"]):
            # 00:00-05:59 は翌日扱いで最後に
            h = int(p["hora_pyt"].split(":")[0])
            sort_h = h + 24 if h < 6 else h
            key = (p["hora_pyt"], p["titulo"][:40])
            if key not in seen:
                seen.add(key)
                uniq.append(p)
        
        # 時間順に再ソート
        uniq = sorted(uniq, key=lambda x: (int(x["hora_pyt"].split(":")[0]) + 24 if int(x["hora_pyt"].split(":")[0]) < 6 else int(x["hora_pyt"].split(":")[0]), int(x["hora_pyt"].split(":")[1])))
        print(f"{date_str}: {len(uniq)} programas reales")
        return uniq
    except Exception as e:
        print(f"[ERROR] {date_str}: {e}")
        return []

if __name__ == "__main__":
    os.makedirs("docs/data", exist_ok=True)
    all_data = {}
    index = []
    today = datetime.date.today()
    
    for i in range(DAYS_TO_FETCH):
        d = today + datetime.timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        programs = fetch_mi_tv(d)
        
        # デモを入れない: 0件なら空のまま保存
        day_data = {"fecha": d_str, "dia_semana": d.strftime("%A"), "programacion": programs}
        with open(f"docs/data/{d_str}.json", "w", encoding="utf-8") as f:
            json.dump(day_data, f, ensure_ascii=False, indent=2)
        all_data[d_str] = day_data
        index.append(d_str)
    
    final = {
        "fecha_actualizacion": datetime.datetime.utcnow().isoformat() + "Z",
        "rango": f"{index[0]} to {index[-1]}",
        "fechas_disponibles": index,
        "programacion_por_fecha": all_data,
        "programacion": all_data[index[0]]["programacion"]
    }
    with open("docs/programacion.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    with open("docs/data/index.json", "w", encoding="utf-8") as f:
        json.dump({"fechas": index, "actualizado": final["fecha_actualizacion"]}, f, ensure_ascii=False, indent=2)
    
    total = sum(len(all_data[d]["programacion"]) for d in index)
    print(f"Done: {len(index)} dias, total {total} programas REALES (sin demo)")
    if total == 0:
        print("WARNING: No se pudo scrapear nada, verifica mi.tv")
