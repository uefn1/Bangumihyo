import requests, json, os, datetime, re, time, zoneinfo, random

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen2:0.5b"
PYT = zoneinfo.ZoneInfo("America/Asuncion")

def ask_qwen(prompt, max_tokens=2048, attempt=1):
    # リトライごとにtemperatureを上げる
    temp = 0.1 + (attempt * 0.15)  # 1回目0.1, 2回目0.25, 3回目0.4
    try:
        r = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "num_ctx": 4096,
                "temperature": temp,
                "top_p": 0.9,
                "num_thread": 4,
                "repeat_penalty": 1.2
            }
        }, timeout=300)
        return r.json().get("response","") if r.status_code==200 else None
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def dynamic_fallback(date_obj_pyt, attempt=0):
    """毎日違う内容にする動的fallback - baseそのまま防止"""
    ds = date_obj_pyt.strftime("%Y-%m-%d")
    wd = date_obj_pyt.weekday()
    day_hash = int(ds.replace("-","")) % 100  # 日付でハッシュ
    
    # 対戦カードを日付でローテーション
    partidos_pool = [
        ("Guaraní vs Libertad", " Olimpia vs Cerro Porteño"),
        ("Cerro Porteño vs Nacional", "Libertad vs Guaraní"),
        (" Olimpia vs Sportivo Luqueño", "Nacional vs Guaraní"),
        ("Libertad vs Olimpia", "Cerro Porteño vs Guaraní"),
        ("Sportivo Trinidense vs Libertad", "Guaraní vs Olimpia"),
    ]
    p1, p2 = partidos_pool[day_hash % len(partidos_pool)]
    
    # 固定番組 + 日替わり対戦
    base = [
        {"hora_pyt":"06:00","titulo":"El Tablón","categoria":"Debate"},
        {"hora_pyt":"08:00","titulo":f"El Tablón - Repetición {ds}","categoria":"Repetición"},
        {"hora_pyt":"10:00","titulo":"Fútbol a lo Grande - Previa","categoria":"Debate"},
        {"hora_pyt":"12:00","titulo":"Fútbol a lo Grande","categoria":"Debate"},
        {"hora_pyt":"14:00","titulo":" Tigo Sports Noticias Mediodía","categoria":"Noticias"},
        {"hora_pyt":"15:00","titulo":f"Primera División - {p1}","categoria":"Fútbol","en_vivo":True},
        {"hora_pyt":"17:00","titulo":f"La Previa - {p2}","categoria":"Previa","en_vivo":False},
        {"hora_pyt":"19:30","titulo":f"Primera División - {p2}","categoria":"Fútbol","en_vivo":True},
        {"hora_pyt":"21:30","titulo":"Tercer Tiempo","categoria":"Debate","en_vivo":False},
        {"hora_pyt":"22:30","titulo":" Tigo Sports Noticias Noche","categoria":"Noticias","en_vivo":False},
    ]
    
    # 週末は追加番組
    if wd >= 5:
        base.append({"hora_pyt":"23:30","titulo":"Fútbol Femenino - Resumen","categoria":"Fútbol Femenino","en_vivo":False})
    
    for p in base:
        p["canal"]=" Tigo Sports"
        p.setdefault("en_vivo", False)
        p["fuente"]=f"{MODEL}-dynamic-fallback-attempt{attempt}"
        p["fecha_pyt"]=ds
        p["timezone"]="America/Asuncion"
        p["is_fallback"]=True
        p["fallback_reason"]="AI failed, dynamic generated"
    
    return base

def generate_with_retry(date_obj_pyt):
    ds_pyt = date_obj_pyt.strftime("%Y-%m-%d")
    weekday_es = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"][date_obj_pyt.weekday()]
    
    # プロンプトを3パターン用意
    prompts = [
        f"""Generate TV schedule for Tigo Sports Paraguay {ds_pyt} ({weekday_es}) PYT.
JSON array 10 items: [{{"hora_pyt":"06:00","titulo":"El Tablón"}},{{"hora_pyt":"12:00","titulo":"Fútbol a lo Grande"}},{{"hora_pyt":"15:00","titulo":"Guaraní vs Libertad"}},{{"hora_pyt":"19:30","titulo":" Olimpia vs Cerro Porteño"}},{{"hora_pyt":"22:30","titulo":"Noticias"}}]
Date {ds_pyt} only. JSON:""",
        
        f"""Crea programación Tigo Sports Paraguay {ds_pyt} {weekday_es} hora Paraguay.
10 programas JSON: 06:00 El Tablón, 12:00 Fútbol a lo Grande, 15:00 Guaraní vs Libertad, 19:30 Olimpia vs Cerro, 22:30 Noticias.
Solo JSON para {ds_pyt}:""",
        
        f"""Tigo Sports {ds_pyt} schedule PYT. 10 shows JSON array.
Must include times: 06:00,08:00,10:00,12:00,14:00,15:00,17:00,19:30,21:30,22:30 with titles El Tablón, Fútbol a lo Grande, Guaraní vs Libertad, Olimpia vs Cerro Porteño.
JSON for {ds_pyt}:"""
    ]
    
    for attempt in range(3):  # 最大3回リトライ
        prompt = prompts[attempt % len(prompts)]
        print(f"[{ds_pyt}] Attempt {attempt+1}/3 - temp {0.1+attempt*0.15}")
        resp = ask_qwen(prompt, max_tokens=2048, attempt=attempt)
        
        if resp:
            clean = resp.replace("```json","").replace("```","")
            start = clean.find('[')
            end = clean.rfind(']')
            if start!=-1 and end!=-1:
                try:
                    data = json.loads(clean[start:end+1])
                    normalized=[]
                    for item in data:
                        h=item.get("hora_pyt") or item.get("hora") or ""
                        if not re.match(r'^\d{2}:\d{2}$', h):
                            continue
                        t=item.get("titulo") or ""
                        if not t or len(t)<3:
                            continue
                        normalized.append({
                            "hora_pyt": h,
                            "titulo": t,
                            "categoria": item.get("categoria") or ("Fútbol" if "vs" in t else "Debate"),
                            "canal": " Tigo Sports",
                            "en_vivo": "vs" in t.lower(),
                            "fuente": f"{MODEL}-attempt{attempt+1}",
                            "fecha_pyt": ds_pyt,
                            "is_fallback": False
                        })
                    normalized=sorted(normalized, key=lambda x: x["hora_pyt"])
                    # 重複排除
                    seen=set()
                    uniq=[]
                    for p in normalized:
                        if p["hora_pyt"] not in seen:
                            seen.add(p["hora_pyt"])
                            uniq.append(p)
                    if len(uniq) >= 6:
                        print(f"[{ds_pyt}] SUCCESS attempt {attempt+1}: {len(uniq)} programs")
                        return uniq
                    else:
                        print(f"[{ds_pyt}] Attempt {attempt+1} too few: {len(uniq)}")
                except Exception as e:
                    print(f"[{ds_pyt}] Attempt {attempt+1} parse fail: {e}")
        
        time.sleep(2)
    
    # 3回失敗したら動的fallback (毎日違う)
    print(f"[{ds_pyt}] All AI attempts failed, using DYNAMIC fallback (not base)")
    return dynamic_fallback(date_obj_pyt, attempt=3)

if __name__ == "__main__":
    os.makedirs("docs/data", exist_ok=True)
    now_pyt = datetime.datetime.now(PYT)
    today_pyt = now_pyt.date()
    start_pyt = today_pyt - datetime.timedelta(days=2)
    
    print(f"PYT now: {now_pyt.isoformat()} - Model: {MODEL} - Retry logic enabled")

    all_data={}
    dates=[]
    fallback_count=0
    ai_count=0
    
    for i in range(7):
        d_pyt = start_pyt + datetime.timedelta(days=i)
        ds = d_pyt.strftime("%Y-%m-%d")
        dates.append(ds)
        progs = generate_with_retry(d_pyt)
        
        # 統計
        if any(p.get("is_fallback") for p in progs):
            fallback_count+=1
        else:
            ai_count+=1
        
        all_data[ds] = {
            "fecha": ds,
            "fecha_pyt": ds,
            "programacion": progs,
            "ai_success": not any(p.get("is_fallback") for p in progs)
        }
        with open(f"docs/data/{ds}.json","w",encoding="utf-8") as f:
            json.dump(all_data[ds], f, ensure_ascii=False, indent=2)
        time.sleep(1)

    final={
        "fecha_actualizacion": datetime.datetime.now(PYT).isoformat(),
        "timezone": "America/Asuncion",
        "rango": f"{dates[0]} to {dates[-1]} (7 días PYT)",
        "fechas_disponibles": dates,
        "programacion_por_fecha": all_data,
        "programacion": all_data[dates[2]]["programacion"],
        "generator": f"{MODEL} - retry + dynamic fallback",
        "stats": {"ai_success": ai_count, "dynamic_fallback": fallback_count, "total": 7},
        "nota": "Baseそのまま出力防止: fallbackは日付で対戦カードが変わる"
    }
    with open("docs/programacion.json","w",encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    
    print(f"DONE: AI {ai_count}/7, Dynamic fallback {fallback_count}/7")
    if fallback_count>0:
        print(f"WARNING: {fallback_count} days used dynamic fallback (but not identical base)")
