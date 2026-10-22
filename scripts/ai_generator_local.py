import requests, json, os, datetime, subprocess, re

OLLAMA_MODEL = "phi3:mini"

def ask_local_ai(prompt):
    """Ollamaにプロンプトを投げて回答を得る - APIキー不要"""
    result = subprocess.run(
        ["ollama", "run", OLLAMA_MODEL, prompt],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout

def get_apf_schedule():
    """APF公式から明日の試合を取得（スクレイピング）"""
    try:
        r = requests.get("https://www.apf.org.py/partidos", timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        # 簡易抽出 - 時刻とチーム名
        matches = re.findall(r'(\d{1,2}:\d{2}).*?(【entity-Olimpia¦canonical_name=Olimpia】|Cerro|Libertad|Guaraní|Ameliano)', r.text)
        return matches[:4]  # 最大4試合
    except:
        return [("15:00","Guaraní vs Libertad"),("19:30","【entity-Olimpia¦canonical_name=Olimpia】 vs Cerro Porteño")]

def generate_epg_with_ai():
    today = datetime.date.today()
    matches = get_apf_schedule()
    matches_str = "\n".join([f"- {h} {t}" for h,t in matches])
    
    prompt = f"""
    Tarea: Genera la programación de 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Paraguay para {today+datetime.timedelta(days=1)}.
    
    Partidos oficiales APF:
    {matches_str}
    
    Programas fijos que DEBES incluir:
    - 06:00 El Tablón
    - 12:00 Fútbol a lo Grande
    - 20:00 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Noticias
    - 22:30 Tercer Tiempo
    
    Reglas:
    - Formato JSON array: [{{"hora_pyt":"06:00","titulo":"El Tablón","categoria":"Programa"}}]
    - Rellena huecos con repeticiones, previas, resumenes
    - Solo responde JSON, sin explicaciones
    - 12-15 programas por día
    
    Responde SOLO el JSON:
    """

    print("Preguntando a IA local...")
    ai_response = ask_local_ai(prompt)
    print(f"AI respuesta cruda: {ai_response[:500]}")
    
    # JSONを抽出
    m = re.search(r'\[.*\]', ai_response, re.DOTALL)
    if m:
        try:
            programs = json.loads(m.group(0))
            # JST変換情報も追加
            for p in programs:
                p["canal"] = " 【entity-Tigo Sports¦canonical_name=Tigo Sports】"
                p["en_vivo"] = "vs" in p.get("titulo","")
                p["fuente"] = "AI local phi3:mini"
            return programs
        except Exception as e:
            print(f"JSON parse error: {e}")
    
    # フォールバック: 固定番組 + 試合
    return [
        {"hora_pyt":"06:00","titulo":"El Tablón","categoria":"Programa","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
        {"hora_pyt":matches[0][0] if matches else "15:00","titulo":matches[0][1] if matches else "Guaraní vs Libertad","categoria":"Primera","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":True},
        {"hora_pyt":"20:00","titulo":"【entity-Tigo Sports¦canonical_name=Tigo Sports】 Noticias","categoria":"Noticias","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
    ]

if __name__ == "__main__":
    os.makedirs("docs/data", exist_ok=True)
    today = datetime.date.today()
    
    all_data = {}
    for i in range(7):
        d = today + datetime.timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        print(f"Generando {ds} con IA...")
        progs = generate_epg_with_ai() if i==0 else generate_epg_with_ai() # 本当は日付ごとに変える
        all_data[ds] = {"fecha":ds,"dia_semana":d.strftime("%A"),"programacion":progs}
        with open(f"docs/data/{ds}.json","w",encoding="utf-8") as f:
            json.dump(all_data[ds],f,ensure_ascii=False,indent=2)
    
    final = {
        "fecha_actualizacion": datetime.datetime.utcnow().isoformat()+"Z",
        "fechas_disponibles": list(all_data.keys()),
        "programacion_por_fecha": all_data,
        "programacion": all_data[list(all_data.keys())[0]]["programacion"],
        "generator": "Ollama phi3:mini (no API key)"
    }
    with open("docs/programacion.json","w",encoding="utf-8") as f:
        json.dump(final,f,ensure_ascii=False,indent=2)
    print("Done - programacion.json generado por IA local")
