import requests, json, os, datetime, re, time

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "tinyllama"

def ask_tiny(prompt, max_tokens=600):
    try:
        r = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": prompt[:500],
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.3,
                "num_ctx": 512,
                "num_thread": 2
            }
        }, timeout=90)
        return r.json().get("response","") if r.status_code==200 else None
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def rule_based_fallback(date_str, is_past=False):
    """日付ごとに少し変える - 過去分は結果付きに"""
    if is_past:
        return [
            {"hora_pyt":"06:00","titulo":"El Tablón - Resumen","categoria":"Debate","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False,"fuente":"tinyllama-fallback-past"},
            {"hora_pyt":"12:00","titulo":"Fútbol a lo Grande - Análisis","categoria":"Debate","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"15:00","titulo":"Primera División - Guaraní 1-1 【entity-Libertad¦canonical_name=Club Libertad】 (Repetición)","categoria":"Fútbol","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"19:30","titulo":"【entity-Olimpia¦canonical_name=Olimpia】 2-0 【entity-Cerro Porteño¦canonical_name=Club Cerro Porteño】 (Repetición)","categoria":"Fútbol","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"22:30","titulo":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Noticias Noche","categoria":"Noticias","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
        ]
    else:
        return [
            {"hora_pyt":"06:00","titulo":"El Tablón","categoria":"Debate","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False,"fuente":"tinyllama-fallback"},
            {"hora_pyt":"08:00","titulo":"El Tablón - Repetición","categoria":"Repetición","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"10:00","titulo":"Fútbol a lo Grande - Previa","categoria":"Debate","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"12:00","titulo":"Fútbol a lo Grande","categoria":"Debate","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"14:00","titulo":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Noticias Mediodía","categoria":"Noticias","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"15:00","titulo":"Primera División - Guaraní vs 【entity-Libertad¦canonical_name=Club Libertad】","categoria":"Fútbol","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":True},
            {"hora_pyt":"17:00","titulo":"La Previa","categoria":"Previa","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"19:30","titulo":"【entity-Olimpia¦canonical_name=Olimpia】 vs 【entity-Cerro Porteño¦canonical_name=Club Cerro Porteño】","categoria":"Fútbol","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":True},
            {"hora_pyt":"21:30","titulo":"Tercer Tiempo","categoria":"Debate","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
            {"hora_pyt":"22:30","titulo":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Noticias Noche","categoria":"Noticias","canal":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】","en_vivo":False},
        ]

def generate_with_tiny(date_obj):
    ds = date_obj.strftime("%Y-%m-%d")
    is_past = date_obj < datetime.date.today()
    
    prompt = f"""Create TV schedule for 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Paraguay {ds}. JSON array:
    [{{"hora":"06:00","titulo":"El Tablon"}},{{"hora":"15:00","titulo":"Guarani vs 【entity-Libertad¦canonical_name=Club Libertad】"}},{{"hora":"19:30","titulo":"【entity-Olimpia¦canonical_name=Olimpia】 vs Cerro"}}]
    10 programs. JSON only:"""
    
    print(f"[{ds}] Asking {MODEL}...")
    resp = ask_tiny(prompt)
    
    if resp:
        m = re.search(r'\[.*\]', resp, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                normalized = []
                for item in data[:12]:
                    h = item.get("hora_pyt") or item.get("hora") or "12:00"
                    t = item.get("titulo") or item.get("title") or "Programa"
                    normalized.append({
                        "hora_pyt": h,
                        "titulo": t,
                        "categoria": item.get("categoria","Fútbol"),
                        "canal": " Tigo Sports",
                        "en_vivo": "vs" in t.lower(),
                        "fuente": MODEL
                    })
                if len(normalized) >= 3:
                    return normalized
            except Exception as e:
                print(f"[{ds}] JSON error: {e}")
    
    return rule_based_fallback(ds, is_past)

if __name__ == "__main__":
    os.makedirs("docs/data", exist_ok=True)
    today = datetime.date.today()
    
    # 変更点: 2日前から7日間
    start_date = today - datetime.timedelta(days=2)
    print(f"Rango: {start_date} から 7日間")
    
    all_data = {}
    dates = []
    for i in range(7):
        d = start_date + datetime.timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        dates.append(ds)
        print(f"Generando {ds} ({'PASADO' if d < today else 'FUTURO'})...")
        progs = generate_with_tiny(d)
        all_data[ds] = {"fecha": ds, "dia_semana": d.strftime("%A"), "programacion": progs}
        with open(f"docs/data/{ds}.json","w",encoding="utf-8") as f:
            json.dump(all_data[ds], f, ensure_ascii=False, indent=2)

    final = {
        "fecha_actualizacion": datetime.datetime.utcnow().isoformat()+"Z",
        "rango": f"{dates[0]} to {dates[-1]} (7 días desde hace 2 días)",
        "fechas_disponibles": dates,
        "programacion_por_fecha": all_data,
        "programacion": all_data[dates[2]]["programacion"], # 今日をデフォルトに
        "generator": f"{MODEL} local - rango 2 dias antes"
    }
    with open("docs/programacion.json","w",encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    
    print(f"Done: {dates[0]} to {dates[-1]}")
