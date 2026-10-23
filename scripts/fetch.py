import re, json, datetime, zoneinfo, os
import snscrape.modules.twitter as sntwitter

PYT = zoneinfo.ZoneInfo("America/Asuncion")

def fetch():
    tweets = []
    try:
        for i, tw in enumerate(sntwitter.TwitterUserScraper("TigoSportsPY").get_items()):
            if i >= 100: break
            txt = tw.rawContent
            if "vs" in txt.lower() or "en vivo" in txt.lower():
                tweets.append({
                    "date": tw.date.astimezone(PYT).isoformat(),
                    "content": txt,
                    "url": tw.url
                })
    except Exception as e:
        print(e)
    return tweets

def to_programacion(tweets):
    by_date = {}
    for t in tweets:
        dt = datetime.datetime.fromisoformat(t["date"])
        fecha = dt.strftime("%Y-%m-%d")
        # 時間抽出 - 固定時間は使わない
        m = re.search(r'(\d{1,2}:\d{2})', t["content"])
        if not m: continue
        hora = m.group(1)
        title = re.sub(r'https?://\S+|#\S+', '', t["content"]).strip()[:120]
        
        by_date.setdefault(fecha, []).append({
            "hora_pyt": hora,
            "titulo": title,
            "en_vivo": True,
            "canal": "Tigo Sports",
            "fecha_pyt": fecha,
            "url_x": t["url"]
        })
    for d in by_date:
        by_date[d] = sorted({p["hora_pyt"]: p for p in sorted(by_date[d], key=lambda x: x["hora_pyt"])}.values(), key=lambda x: x["hora_pyt"])
    return by_date

if __name__ == "__main__":
    tweets = fetch()
    by_date = to_programacion(tweets)
    
    # 7日分保証 - Xにデータが無い日は空
    now = datetime.datetime.now(PYT).date()
    for i in range(-2,5):
        d = (now + datetime.timedelta(days=i)).isoformat()
        by_date.setdefault(d, [])
    
    all_progs = []
    for d in sorted(by_date.keys()):
        all_progs.extend(by_date[d])

    out = {
        "fecha_actualizacion": datetime.datetime.now(PYT).isoformat(),
        "fuente": "X @TigoSportsPY via snscrape",
        "fechas_disponibles": sorted(by_date.keys()),
        "programacion_por_fecha": {d: {"fecha": d, "programacion": by_date[d]} for d in sorted(by_date.keys())},
        "programacion": by_date.get(now.isoformat(), []),
        "epg": [{"start_pyt": f"{p['fecha_pyt']} {p['hora_pyt']}", "title": p["titulo"], "live": p["en_vivo"]} for p in all_progs]
    }
    
    os.makedirs("docs", exist_ok=True)
    with open("docs/programacion.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"done {len(all_progs)} programs")
