import requests, json, datetime, os
from bs4 import BeautifulSoup

def fetch_mi_tv():
    url = "https://mi.tv/py/canales/tigo-sports"
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
                    "hora": time_el.get_text(strip=True)[:10],
                    "titulo": title_el.get_text(strip=True)[:120],
                    "canal": "Tigo Sports",
                    "categoria": "Fútbol",
                    "en_vivo": "vivo" in txt or "en vivo" in txt
                })
        # 重複除去
        seen = set()
        uniq = []
        for p in programs:
            k = (p["hora"], p["titulo"])
            if k not in seen:
                seen.add(k)
                uniq.append(p)
        return uniq[:30]
    except Exception as e:
        print(f"[WARN] mi.tv failed: {e}")
        return []

def fetch_fallback():
    return [
        {"hora": "15:00", "titulo": "Cerro Porteño vs Sportivo Ameliano", "canal": "Tigo Sports", "categoria": "Primera División", "en_vivo": True},
        {"hora": "17:20", "titulo": "Sportivo Luqueño vs Sportivo San Lorenzo", "canal": "Tigo Sports +", "categoria": "Primera División", "en_vivo": True},
        {"hora": "19:30", "titulo": "El Tablón - Análisis fecha", "canal": "Tigo Sports", "categoria": "Programa", "en_vivo": False},
        {"hora": "21:00", "titulo": "Copa Libertadores - Resumen", "canal": "Tigo Sports +", "categoria": "Internacional", "en_vivo": False},
    ]

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)

    programs = fetch_mi_tv()
    if len(programs) < 2:
        print("Usando fallback data")
        programs = fetch_fallback()

    # UTCで保存、表示はJS側で America/Asuncion に変換
    data = {
        "fecha_actualizacion": datetime.datetime.utcnow().isoformat() + "Z",
        "fuente": "mi.tv / fallback",
        "programacion": programs
    }
    with open("docs/programacion.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(programs)} programs to docs/programacion.json")
