import datetime, random, hashlib, json, requests, zoneinfo

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen2:0.5b"
PYT = zoneinfo.ZoneInfo("America/Asuncion")

def ask_qwen(prompt):
    try:
        r = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 2048, "num_ctx": 4096, "temperature": 0.7, "top_p": 0.9}
        }, timeout=120)
        return r.json().get("response","") if r.status_code==200 else None
    except:
        return None

def fully_dynamic_fallback(date_obj_pyt):
    """チームプールも時間固定もなし - 完全ランダム"""
    ds = date_obj_pyt.strftime("%Y-%m-%d")
    seed = int(hashlib.md5(ds.encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    
    # 時間もランダム生成 - 固定リストなし
    # 朝6時から夜23時までランダムに10個
    horas = sorted([f"{rnd.randint(6,23):02d}:{rnd.choice(['00','15','30','45'])}" for _ in range(10)])
    # 重複排除
    horas = sorted(list(dict.fromkeys(horas)))  
    while len(horas) < 6:  # 最低6個
        horas.append(f"{rnd.randint(6,23):02d}:00")
        horas = sorted(list(dict.fromkeys(horas)))
    
    # タイトルも完全に自由 - プールなし
    # AIに考えさせる代わりに、シードから文章生成的な
    verbos = ["Análisis", "En Vivo", "Previa", "Resumen", "Debate", "Noticias", "Especial", "Final"]
    
    programacion = []
    for h in horas[:10]:
        # シードからタイトル生成 - 例リスト参照なし
        titulo_seed = f"{ds}-{h}-{seed}"
        titulo_hash = hashlib.md5(titulo_seed.encode()).hexdigest()
        
        if rnd.random() < 0.5:
            # サッカーっぽいタイトルを自由生成
            titulo = f"Programa {titulo_hash[:4]} - {rnd.choice(verbos)}"
        else:
            titulo = f"{rnd.choice(verbos)} 【entity-Tigo Sports¦canonical_name=Tigo Sports】"
        
        programacion.append({
            "hora_pyt": h,
            "titulo": titulo,
            "categoria": rnd.choice(["Fútbol", "Debate", "Noticias", "Análisis"]),
            "canal": " 【entity-Tigo Sports¦canonical_name=Tigo Sports】",
            "en_vivo": rnd.random() > 0.5,
            "fuente": "fully-dynamic-no-pool",
            "fecha_pyt": ds,
            "seed": seed,
            "no_fixed_example": True,
            "no_team_pool": True,
            "no_fixed_time": True
        })
    
    return sorted(programacion, key=lambda x: x["hora_pyt"])

def generate_fully_free(date_obj_pyt):
    """AIにも固定を与えない - 完全に自由"""
    ds = date_obj_pyt.strftime("%Y-%m-%d")
    seed = int(hashlib.md5(ds.encode()).hexdigest()[:8], 16)
    
    # プロンプトにもチーム名も時間も書かない
    prompt = f"""Date {ds}
Channel 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Paraguay PYT
Create TV schedule.
You decide everything: times, titles, categories.
10 programs.
Seed {seed} makes it unique.
JSON array with hora_pyt, titulo, categoria.
Be creative."""
    
    resp = ask_qwen(prompt)
    if resp:
        try:
            import re
            s = resp.find('[')
            e = resp.rfind(']')
            if s!=-1 and e!=-1:
                data = json.loads(resp[s:e+1])
                if len(data) >= 4:
                    # 時間もタイトルもAIが自由に決めたものをそのまま使う
                    return [{
                        "hora_pyt": d.get("hora_pyt") or d.get("hora") or "12:00",
                        "titulo": d.get("titulo") or "Programa",
                        "categoria": d.get("categoria") or "General",
                        "canal": " Tigo Sports",
                        "fuente": MODEL,
                        "fecha_pyt": ds,
                        "fully_free": True
                    } for d in data[:10]]
        except:
            pass
    
    return fully_dynamic_fallback(date_obj_pyt)

# 実行
if __name__ == "__main__":
    import os
    os.makedirs("docs/data", exist_ok=True)
    now_pyt = datetime.datetime.now(PYT)
    start = now_pyt.date() - datetime.timedelta(days=2)
    
    all_data = {}
    dates = []
    for i in range(7):
        d = start + datetime.timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        dates.append(ds)
        progs = generate_fully_free(d)
        all_data[ds] = {"fecha": ds, "programacion": progs}
    
    final = {
        "fecha_actualizacion": now_pyt.isoformat(),
        "fechas_disponibles": dates,
        "programacion_por_fecha": all_data,
        "programacion": all_data[dates[2]]["programacion"],
        "generator": "fully-free-no-pool-no-fixed-time",
        "note": "チームプールなし、時間固定なし、例なし - 完全自由生成"
    }
    with open("docs/programacion.json","w",encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
