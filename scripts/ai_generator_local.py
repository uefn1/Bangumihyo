import requests, json, os, datetime, re, time

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen2:0.5b"  # 350MB, tinyllamaより賢い

def ask_qwen(prompt, max_tokens=800):
    """qwen2:0.5bは日本語・スペイン語・JSONが得意"""
    try:
        r = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.2,  # 低めにしてJSON精度UP
                "num_ctx": 1024,
                "num_thread": 2
            }
        }, timeout=120)
        if r.status_code == 200:
            return r.json().get("response","")
        else:
            print(f"Ollama {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def fallback(date_str):
    return [
        {"hora_pyt":"06:00","titulo":"El Tablón","categoria":"Debate","canal":" Tigo Sports","en_vivo":False,"fuente":f"{MODEL}-fallback"},
        {"hora_pyt":"08:00","titulo":"El Tablón - Repetición","categoria":"Repetición","canal":" Tigo Sports","en_vivo":False},
        {"hora_pyt":"10:00","titulo":"Fútbol a lo Grande - Previa","categoria":"Debate","canal":" Tigo Sports","en_vivo":False},
        {"hora_pyt":"12:00","titulo":"Fútbol a lo Grande","categoria":"Debate","canal":" Tigo Sports","en_vivo":False},
        {"hora_pyt":"14:00","titulo":" Tigo Sports Noticias Mediodía","categoria":"Noticias","canal":" Tigo Sports","en_vivo":False},
        {"hora_pyt":"15:00","titulo":"Guaraní vs 【entity-Libertad¦canonical_name=Club Libertad】","categoria":"Fútbol","canal":" Tigo Sports","en_vivo":True},
        {"hora_pyt":"17:00","titulo":"La Previa - Guaraní vs 【entity-Libertad¦canonical_name=Club Libertad】","categoria":"Previa","canal":" Tigo Sports","en_vivo":False},
        {"hora_pyt":"19:30","titulo":" 【entity-Olimpia¦canonical_name=Olimpia】 vs 【entity-Cerro Porteño¦canonical_name=Club Cerro Porteño】","categoria":"Fútbol","canal":" Tigo Sports","en_vivo":True},
        {"hora_pyt":"21:30","titulo":"Tercer Tiempo","categoria":"Debate","canal":" Tigo Sports","en_vivo":False},
        {"hora_pyt":"22:30","titulo":" Tigo Sports Noticias Noche","categoria":"Noticias","canal":" Tigo Sports","en_vivo":False},
    ]

def generate_one_day(date_obj):
    ds = date_obj.strftime("%Y-%m-%d")
    # qwen2向けプロンプト: 英語+スペイン語ミックスが最も精度高い
    prompt = f"""You are a TV schedule generator for Tigo Sports Paraguay.
Date: {ds}
Generate 10 programs in JSON array format.
Must include: 06:00 El Tablón, 12:00 Fútbol a lo Grande, 15:00 Guaraní vs 【entity-Libertad¦canonical_name=Club Libertad】, 19:30 【entity-Olimpia¦canonical_name=Olimpia】 vs 【entity-Cerro Porteño¦canonical_name=Club Cerro Porteño】, 22:30 Noticias
Format: [{{"hora_pyt":"06:00","titulo":"El Tablón","categoria":"Debate"}}, ...]
Rules: JSON only, no explanation, 10 items, times sorted, use Spanish.
JSON:"""

    print(f"[{ds}] Asking {MODEL}...")
    t0=time.time()
    resp = ask_qwen(prompt, max_tokens=800)
    elapsed=time.time()-t0
    print(f"[{ds}] Response in {elapsed:.1f}s, len={len(resp) if resp else 0}")

    if resp:
        # JSON配列を抽出 (```json 対応)
        resp_clean = resp.replace("```json","").replace("```","")
        m = re.search(r'\[.*\]', resp_clean, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                normalized=[]
                for item in data:
                    h = item.get("hora_pyt") or item.get("hora") or item.get("time") or "12:00"
                    # 時刻フォーマット修正
                    if not re.match(r'^\d{2}:\d{2}$', h):
                        continue
                    t = item.get("titulo") or item.get("title") or "Programa"
                    normalized.append({
                        "hora_pyt": h,
                        "titulo": t,
                        "categoria": item.get("categoria") or ("Fútbol" if "vs" in t else "Debate"),
                        "canal": " Tigo Sports",
                        "en_vivo": "vs" in t.lower(),
                        "fuente": MODEL
                    })
                # ソート + 重複排除
                normalized = sorted(normalized, key=lambda x: x["hora_pyt"])
                seen=set()
                uniq=[]
                for p in normalized:
                    if p["hora_pyt"] not in seen:
                        seen.add(p["hora_pyt"])
                        uniq.append(p)
                if len(uniq) >= 6:
                    print(f"[{ds}] OK: {len(uniq)} programs from AI")
                    return uniq
                else:
                    print(f"[{ds}] Too few ({len(uniq)}), using fallback")
            except Exception as e:
                print(f"[{ds}] JSON parse fail: {e}, raw={resp[:400]}")

    print(f"[{ds}] Fallback")
    return fallback(ds)

if __name__ == "__main__":
    os.makedirs("docs/data", exist_ok=True)
    today = datetime.date.today()
    start = today - datetime.timedelta(days=2)  # 2日前から
    
    all_data={}
    dates=[]
    for i in range(7):
        d = start + datetime.timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        dates.append(ds)
        progs = generate_one_day(d)
        all_data[ds] = {"fecha": ds, "dia_semana": d.strftime("%A"), "programacion": progs}
        with open(f"docs/data/{ds}.json","w",encoding="utf-8") as f:
            json.dump(all_data[ds], f, ensure_ascii=False, indent=2)
        time.sleep(1)  # Ollamaを休ませる

    final={
        "fecha_actualizacion": datetime.datetime.utcnow().isoformat()+"Z",
        "rango": f"{dates[0]} to {dates[-1]} (7 días desde hace 2 días)",
        "fechas_disponibles": dates,
        "programacion_por_fecha": all_data,
        "programacion": all_data[dates[2]]["programacion"],  # 今日
        "generator": f"{MODEL} local - 350MB"
    }
    with open("docs/programacion.json","w",encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"DONE: {dates[0]} to {dates[-1]} - all with {MODEL}")
