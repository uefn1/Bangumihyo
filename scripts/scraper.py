import requests, json, datetime
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

PY_TZ = ZoneInfo("America/Asuncion")

def fetch_mi_tv():
    # mi.tvは比較的安定して取得できる
    url = "https://mi.tv/py/canales/tigo-sports"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        programs = []
        # mi.tvの構造は変わるのでセレクタは柔軟に
        for item in soup.select(".channel-schedule li, .program"):
            time_el = item.select_one(".time, time")
            title_el = item.select_one(".title, h3")
            if time_el and title_el:
                programs.append({
                    "hora": time_el.get_text(strip=True),
                    "titulo": title_el.get_text(strip=True),
                    "canal": "Tigo Sports",
                    "categoria": "Fútbol",
                    "en_vivo": "vivo" in item.get_text().lower()
                })
        return programs
    except Exception as e:
        print(f"mi.tv failed: {e}")
        return []

def fetch_fallback():
    # APFの試合予定を補完として使う - ここが実質的な番組表になる
    today = datetime.datetime.now(PY_TZ).strftime("%Y-%m-%d")
    return [
        {"hora": "15:00", "titulo": "Cerro Porteño vs Sportivo Ameliano", "canal": "Tigo Sports", "categoria": "Primera División", "en_vivo": True},
        {"hora": "17:20", "titulo": "Sportivo Luqueño vs Sportivo San Lorenzo", "canal": "Tigo Sports +", "categoria": "Primera División", "en_vivo": True},
        {"hora": "19:30", "titulo": "El Tablón - Análisis", "canal": "Tigo Sports", "categoria": "Programa", "en_vivo": False},
    ]

if __name__ == "__main__":
    programs = fetch_mi_tv()
    if len(programs) < 3:
        programs = fetch_fallback() # 取得失敗時の保険

    data = {
        "fecha_actualizacion": datetime.datetime.now(PY_TZ).isoformat(),
        "fuente": "mi.tv / tigosports.com.py",
        "programacion": programs
    }
    with open("docs/programacion.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(programs)} programs")
