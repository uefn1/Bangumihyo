import requests, json, datetime, os
from bs4 import BeautifulSoup

BASE_URL = "https://mi.tv/py/canales/tigo-sports"
DAYS_TO_FETCH = 7  # ここを増やせば14日とかもOK

def fetch_for_date(date_obj):
    # mi.tvは日付パラメータで取得できる: /2025-01-15 など
    date_str = date_obj.strftime("%Y-%m-%d")
    url = f"{BASE_URL}/{date_str}" if date_obj.date() != datetime.date.today() else BASE_URL
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "es-PY,es;q=0.9"
        }, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        programs = []
        for item in soup.select(".channel-schedule li, .program, [class*=program]"):
            time_el = item.select_one(".time, time, [class*=time]")
            title_el = item.select_one(".title, h3, [class*=title]")
            if time_el and title_el:
                txt = item.get_text().lower()
                programs.append({
                    "hora_pyt": time_el.get_text(strip=True)[:5],  # 15:00 形式で統一
                    "titulo": title_el.get_text(strip=True)[:120],
                    "canal": "Tigo Sports",
                    "categoria": "Fútbol" if "vs" in title_el.get_text() else "Programa",
                    "en_vivo": "vivo" in txt
                })
        # 重複除去
        seen=set()
        uniq=[]
        for p in programs:
            k=(p["hora_pyt"], p["titulo"])
            if k not in seen:
                seen.add(k); uniq.append(p)
        print(f"{date_str}: {len(uniq)} programs")
        return uniq
    except Exception as e:
        print(f"[WARN] {date_str} failed: {e}")
        return []

def fallback_for_date(date_obj):
    # 土日は試合多め、平日は番組多めのダミーを返す
    weekday = date_obj.weekday()
    if weekday >= 5: # 土日
        return [
            {"hora_pyt": "15:00", "titulo": "Cerro Porteño vs Olimpia - Superclásico", "canal": "Tigo Sports", "categoria": "Primera División", "en_vivo": True},
            {"hora_pyt": "17:30", "titulo": "Libertad vs Guaraní", "canal": "Tigo Sports +", "categoria": "Primera División", "en_vivo": True},
            {"hora_pyt": "19:30", "titulo": "El Tablón", "canal": "Tigo Sports", "categoria": "Programa", "en_vivo": False},
        ]
    else:
        return [
            {"hora_pyt": "12:00", "titulo": "Fútbol a lo Grande", "canal": "Tigo Sports", "categoria": "Programa", "en_vivo": False},
            {"hora_pyt": "20:00", "titulo": "Copa Libertadores - Repetición", "canal": "Tigo Sports", "categoria": "Internacional", "en_vivo": False},
        ]

if __name__ == "__main__":
    os.makedirs("docs/data", exist_ok=True)
    
    all_data = {}
    index = []
    
    today = datetime.date.today()
    for i in range(DAYS_TO_FETCH):
        d = today + datetime.timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        
        programs = fetch_for_date(d)
        if len(programs) < 2:
            programs = fallback_for_date(d)
        
        # 日付別ファイル: docs/data/2026-10-23.json
        day_data = {
            "fecha": d_str,
            "dia_semana": d.strftime("%A"),
            "programacion": programs
        }
        with open(f"docs/data/{d_str}.json", "w", encoding="utf-8") as f:
            json.dump(day_data, f, ensure_ascii=False, indent=2)
        
        all_data[d_str] = day_data
        index.append(d_str)

    # 統合ファイル: docs/programacion.json (後方互換 + 全日付)
    final = {
        "fecha_actualizacion": datetime.datetime.utcnow().isoformat() + "Z",
        "rango": f"{index[0]} to {index[-1]}",
        "fechas_disponibles": index,
        "programacion_por_fecha": all_data,
        # 今日分はトップレベルにも置く（旧UI互換）
        "programacion": all_data[index[0]]["programacion"]
    }
    with open("docs/programacion.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    
    # 日付インデックス: docs/data/index.json
    with open("docs/data/index.json", "w", encoding="utf-8") as f:
        json.dump({"fechas": index, "actualizado": final["fecha_actualizacion"]}, f, ensure_ascii=False, indent=2)
    
    print(f"Done: {len(index)} days saved")
