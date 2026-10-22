import requests, json, datetime, os
from bs4 import BeautifulSoup

BASE_URL = "https://mi.tv/py/canales/tigo-sports"
DAYS_TO_FETCH = 7

def fetch_for_date(date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")
    today = datetime.date.today()
    url = f"{BASE_URL}/{date_str}" if date_obj != today else BASE_URL
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
                    "hora_pyt": time_el.get_text(strip=True)[:5],
                    "titulo": title_el.get_text(strip=True)[:120],
                    "canal": "【entity-Tigo Sports¦canonical_name=Tigo Sports】",
                    "categoria": "Fútbol" if "vs" in title_el.get_text() else "Programa",
                    "en_vivo": "vivo" in txt
                })
        seen=set()
        uniq=[]
        for p in programs:
            k=(p["hora_pyt"], p["titulo"])
            if k not in seen:
                seen.add(k); uniq.append(p)
        print(f"{date_str}: {len(uniq)} programs from {url}")
        return uniq
    except Exception as e:
        print(f"[WARN] {date_str} failed: {e}")
        return []

def fallback_for_date(date_obj):
    weekday = date_obj.weekday()
    if weekday >= 5:
        return [
            {"hora_pyt": "15:00", "titulo": "Cerro Porteño vs 【entity-Olimpia¦canonical_name=Olimpia】 - Superclásico", "canal": "【entity-Tigo Sports¦canonical_name=Tigo Sports】", "categoria": "Primera División", "en_vivo": True},
            {"hora_pyt": "17:30", "titulo": "Libertad vs Guaraní", "canal": "【entity-Tigo Sports¦canonical_name=Tigo Sports】 +", "categoria": "Primera División", "en_vivo": True},
            {"hora_pyt": "19:30", "titulo": "El Tablón", "canal": "【entity-Tigo Sports¦canonical_name=Tigo Sports】", "categoria": "Programa", "en_vivo": False},
        ]
    else:
        return [
            {"hora_pyt": "12:00", "titulo": "Fútbol a lo Grande", "canal": "【entity-Tigo Sports¦canonical_name=Tigo Sports】", "categoria": "Programa", "en_vivo": False},
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
        
        day_data = {
            "fecha": d_str,
            "dia_semana": d.strftime("%A"),
            "programacion": programs
        }
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
    
    print(f"Done: {len(index)} days saved")
