import requests, json, os, datetime, re, time

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "tinyllama"  # 450MB, 起動3秒、生成20秒

def ask_tiny(prompt, max_tokens=500):
    """Ollama APIで高速生成 - subprocessではなくHTTP API"""
    # tinyllamaは長いプロンプトが苦手なので短くする
    short_prompt = prompt[:400]  
    
    try:
        r = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": short_prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,  # 生成文字数を制限
                "temperature": 0.3,
                "num_ctx": 512,  # コンテキストを小さくして高速化
                "num_thread": 2
            }
        }, timeout=90)  # 90秒でタイムアウト
        
        if r.status_code == 200:
            return r.json().get("response","")
        else:
            print(f"Ollama error {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"Ollama exception: {e}")
        return None

def rule_based_fallback(date_str):
    """tinyllamaが失敗しても絶対に動くフォールバック"""
    base = [
        {"hora_pyt":"06:00","titulo":"El Tablón","categoria":"Debate"},
        {"hora_pyt":"08:00","titulo":"El Tablón - Repetición","categoria":"Repetición"},
        {"hora_pyt":"10:00","titulo":"Fútbol a lo Grande - Previa","categoria":"Debate"},
        {"hora_pyt":"12:00","titulo":"Fútbol a lo Grande","categoria":"Debate"},
        {"hora_pyt":"14:00","titulo":"【entity-Tigo Sports¦canonical_name=Tigo Sports】 Noticias Mediodía","categoria":"Noticias"},
        {"hora_pyt":"15:00","titulo":"Primera División - Guaraní vs Libertad","categoria":"Fútbol","en_vivo":True},
        {"hora_pyt":"17:00","titulo":"La Previa","categoria":"Previa"},
        {"hora_pyt":"19:30","titulo":"Olimpia vs Cerro Porteño","categoria":"Fútbol","en_vivo":True},
        {"hora_pyt":"21:30","titulo":"Tercer Tiempo","categoria":"Debate"},
        {"hora_pyt":"22:30","titulo":" 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Noticias Noche","categoria":"Noticias"},
    ]
    for p in base:
        p["canal"] = " 【entity-Tigo Sports¦canonical_name=Tigo Sports】"
        p.setdefault("en_vivo", "vs" in p["titulo"])
        p["fuente"] = "tinyllama-fallback"
    return base

def generate_with_tiny(date_obj):
    ds = date_obj.strftime("%Y-%m-%d")
    
    # tinyllama向けに超短いプロンプト
    prompt = f"""Create TV schedule for 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Paraguay {ds}. JSON array only:
    [{{"hora":"06:00","titulo":"El Tablon"}},{{"hora":"12:00","titulo":"Futbol a lo Grande"}},{{"hora":"15:00","titulo":"Guarani vs Libertad"}},{{"hora":"19:30","titulo":"Olimpia vs Cerro"}}]
    Need 10 programs. JSON only:"""
    
    print(f"[{ds}] Asking tinyllama...")
    start = time.time()
    resp = ask_tiny(prompt, max_tokens=600)
    elapsed = time.time() - start
    print(f"[{ds}] Done in {elapsed:.1f}s, resp len {len(resp) if resp else 0}")
    
    if resp:
        # JSON抽出
        m = re.search(r'\[.*\]', resp, re.DOTALL)
        if m:
            try:
                # tinyllamaは "hora" と書くことがあるので正規化
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
                        "fuente": f"{MODEL}"
                    })
                if len(normalized) >= 5:
                    return normalized
            except Exception as e:
                print(f"JSON error: {e}")
    
    print(f"[{ds}] Using fallback")
    return rule_based_fallback(ds)

if __name__ == "__main__":
    os.makedirs("docs/data", exist_ok=True)
    today = datetime.date.today()
    
    all_data = {}
    for i in range(2):  # まずは2日間だけにして高速化 (7日間だと7*20秒=140秒)
        d = today + datetime.timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        progs = generate_with_tiny(d)
        all_data[ds] = {"fecha": ds, "dia_semana": d.strftime("%A"), "programacion": progs}
        with open(f"docs/data/{ds}.json","w",encoding="utf-8") as f:
            json.dump(all_data[ds], f, ensure_ascii=False, indent=2)
    
    # 残りの5日間はコピーで高速化
    base_progs = list(all_data.values())[0]["programacion"]
    for i in range(2,7):
        d = today + datetime.timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        all_data[ds] = {"fecha": ds, "dia_semana": d.strftime("%A"), "programacion": base_progs}
        with open(f"docs/data/{ds}.json","w",encoding="utf-8") as f:
            json.dump(all_data[ds], f, ensure_ascii=False, indent=2)

    final = {
        "fecha_actualizacion": datetime.datetime.utcnow().isoformat()+"Z",
        "fechas_disponibles": list(all_data.keys()),
        "programacion_por_fecha": all_data,
        "programacion": all_data[list(all_data.keys())[0]]["programacion"],
        "generator": f"{MODEL} local (no API key, lightweight)"
    }
    with open("docs/programacion.json","w",encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print("Done - lightweight model finished")
