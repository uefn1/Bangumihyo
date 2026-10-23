import re, json, datetime, zoneinfo, os, requests

PYT = zoneinfo.ZoneInfo("America/Asuncion")

def fetch_via_fxtwitter():
    headers = {"User-Agent": "Mozilla/5.0"}
    urls = [
        "https://api.fxtwitter.com/TigoSportsPY",
    ]
    for api_url in urls:
        try:
            print(f"Trying {api_url}")
            r = requests.get(api_url, headers=headers, timeout=30)
            print(f"Status {r.status_code}")
            if r.status_code != 200:
                print(r.text[:1000])
                continue
            
            data = r.json()
            print(f"Keys: {list(data.keys())[:10]}")
            
            # fxtwitterの実際の構造をログ
            # 構造1: {"code":200,"user":{"tweets":[...]}}
            # 構造2: {"tweet":...} ではない
            
            tweets_raw = []
            if isinstance(data, dict):
                if "user" in data and isinstance(data["user"], dict):
                    tweets_raw = data["user"].get("timeline", []) or data["user"].get("tweets", [])
                elif "timeline" in data:
                    tweets_raw = data["timeline"]
                elif "tweets" in data:
                    tweets_raw = data["tweets"]
                # codeが200以外なら失敗
                if data.get("code") != 200 and "code" in data:
                    print(f"API error code: {data}")
                    continue
            
            print(f"Raw tweets type: {type(tweets_raw)}, len: {len(tweets_raw) if hasattr(tweets_raw,'__len__') else 'N/A'}")
            if isinstance(tweets_raw, int):
                print(f"tweets_raw is int: {tweets_raw} - API changed")
                continue
            
            tweets = []
            for tw in tweets_raw[:100]:
                if not isinstance(tw, dict):
                    continue
                text = tw.get("text", "") or tw.get("full_text", "") or ""
                if not text:
                    # nested tweet
                    if "tweet" in tw:
                        text = tw["tweet"].get("text","")
                if "vs" not in text.lower() and "en vivo" not in text.lower():
                    # vsがなくても時間があるものは拾う
                    if not re.search(r'\d{1,2}:\d{2}', text):
                        continue
                
                tw_id = tw.get("id", "") or tw.get("id_str", "")
                tweets.append({
                    "date": datetime.datetime.now(PYT).isoformat(),
                    "content": text,
                    "url": f"https://twitter.com/TigoSportsPY/status/{tw_id}" if tw_id else "https://twitter.com/TigoSportsPY"
                })
            
            if tweets:
                print(f"fxtwitter success {len(tweets)}")
                return tweets
                
        except Exception as e:
            print(f"fxtwitter failed: {e}")
            import traceback
            traceback.print_exc()
            continue
    return []

def fetch_via_fixupx():
    """別のプロキシ: api.fixupx.com"""
    try:
        url = "https://api.fixupx.com/TigoSportsPY"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        print(f"fixupx status {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            tweets_raw = data.get("user", {}).get("timeline", [])
            tweets = []
            for tw in tweets_raw[:50]:
                if not isinstance(tw, dict): continue
                text = tw.get("text","")
                if "vs" in text.lower():
                    tweets.append({
                        "date": datetime.datetime.now(PYT).isoformat(),
                        "content": text,
                        "url": "https://twitter.com/TigoSportsPY"
                    })
            if tweets:
                return tweets
    except Exception as e:
        print(f"fixupx failed {e}")
    return []

if __name__ == "__main__":
    print("=== Fetch start ===")
    tweets = fetch_via_fxtwitter()
    if not tweets:
        tweets = fetch_via_fixupx()
    
    print(f"Total tweets: {len(tweets)}")
    
    prog_path = "docs/programacion.json"
    
    # 0件でも古いファイルを消さない処理
    if len(tweets) == 0:
        print("No tweets - keeping old file")
        if os.path.exists(prog_path):
            with open(prog_path,"r",encoding="utf-8") as f:
                old = json.load(f)
            old["fecha_actualizacion"] = datetime.datetime.now(PYT).isoformat()
            old["debug_last_error"] = "fxtwitter 403/cloudflare, kept old"
            with open(prog_path,"w",encoding="utf-8") as f:
                json.dump(old, f, ensure_ascii=False, indent=2)
        else:
            # 初回でファイルがない場合だけダミー生成
            now = datetime.datetime.now(PYT).date().isoformat()
            os.makedirs("docs", exist_ok=True)
            dummy = {
                "fecha_actualizacion": datetime.datetime.now(PYT).isoformat(),
                "fuente": "fallback - X blocked",
                "fechas_disponibles": [now],
                "programacion_por_fecha": {now: {"fecha": now, "programacion": []}},
                "programacion": [],
                "epg": []
            }
            with open(prog_path,"w",encoding="utf-8") as f:
                json.dump(dummy, f, ensure_ascii=False, indent=2)
        exit(0)
    
    # パース
    by_date = {}
    for t in tweets:
        m = re.search(r'(\d{1,2}:\d{2})', t["content"])
        hora = m.group(1) if m else "19:30"
        title = re.sub(r'https?://\S+|#\S+', '', t["content"]).strip()[:120]
        fecha = datetime.datetime.now(PYT).strftime("%Y-%m-%d")
        by_date.setdefault(fecha, []).append({
            "hora_pyt": hora,
            "titulo": title,
            "en_vivo": True,
            "canal": "【entity-Tigo Sports¦canonical_name=Tigo Sports】",
            "fecha_pyt": fecha,
            "url_x": t["url"]
        })
    
    now = datetime.datetime.now(PYT).date()
    for i in range(-2,5):
        d = (now + datetime.timedelta(days=i)).isoformat()
        by_date.setdefault(d, [])
    
    all_progs = [p for progs in by_date.values() for p in progs]
    out = {
        "fecha_actualizacion": datetime.datetime.now(PYT).isoformat(),
        "fuente": "X @TigoSportsPY via fxtwitter",
        "fechas_disponibles": sorted(by_date.keys()),
        "programacion_por_fecha": {d: {"fecha": d, "programacion": by_date[d]} for d in sorted(by_date.keys())},
        "programacion": by_date.get(now.isoformat(), []),
        "epg": [{"start_pyt": f"{p['fecha_pyt']} {p['hora_pyt']}", "title": p["titulo"], "live": p["en_vivo"]} for p in all_progs],
        "debug_tweets_count": len(tweets)
    }
    
    os.makedirs("docs", exist_ok=True)
    with open(prog_path,"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"done {len(all_progs)}")
