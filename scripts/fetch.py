import re, json, datetime, zoneinfo, os, requests, time

PYT = zoneinfo.ZoneInfo("America/Asuncion")

def fetch_via_fxtwitter():
    """FixTweet API - GitHub Actionsからでも動く"""
    tweets = []
    # 1. ユーザーのツイートを取得
    urls = [
        "https://api.fxtwitter.com/TigoSportsPY",
        "https://api.vxtwitter.com/TigoSportsPY"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for api_url in urls:
        try:
            print(f"Trying {api_url}")
            r = requests.get(api_url, headers=headers, timeout=30)
            print(f"Status {r.status_code}")
            if r.status_code != 200:
                print(r.text[:500])
                continue
            
            data = r.json()
            # fxtwitterの構造
            user_tweets = data.get("user", {}).get("tweets", []) or data.get("tweets", []) or []
            # 別の構造の場合
            if not user_tweets and "timeline" in data:
                user_tweets = data["timeline"]
            
            for tw in user_tweets[:100]:
                # twはdictかstr
                if isinstance(tw, dict):
                    text = tw.get("text", "") or tw.get("rawContent", "") or ""
                    tw_id = tw.get("id", "")
                    created = tw.get("created_at", "") or tw.get("created_timestamp", "")
                else:
                    text = str(tw)
                    tw_id = ""
                    created = ""
                
                if "vs" in text.lower() or "en vivo" in text.lower():
                    tweets.append({
                        "date": datetime.datetime.now(PYT).isoformat(),
                        "content": text,
                        "url": f"https://twitter.com/TigoSportsPY/status/{tw_id}" if tw_id else "https://twitter.com/TigoSportsPY"
                    })
            
            if tweets:
                print(f"fxtwitter success {len(tweets)}")
                return tweets
                
        except Exception as e:
            print(f"fxtwitter {api_url} failed: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return []

def fetch_via_syndication():
    """Twitter syndication - まだ生きている古いAPI"""
    try:
        # TigoSportsPYのIDは要調査だが、usernameで試す
        url = "https://syndication.twitter.com/srv/timeline-profile/screen-name/TigoSportsPY?showReplies=false"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            data = r.json()
            tweets = []
            for tw in data.get("body", [])[:50]:
                txt = tw.get("full_text", "") or tw.get("text", "")
                if "vs" in txt.lower():
                    tweets.append({
                        "date": datetime.datetime.now(PYT).isoformat(),
                        "content": txt,
                        "url": "https://twitter.com/TigoSportsPY"
                    })
            if tweets:
                return tweets
    except Exception as e:
        print(f"syndication failed {e}")
    return []

def fetch_via_nitter_scraper():
    """最後の手段: nitterインスタンスを総当たり"""
    # 2026年10月時点で生きてる可能性があるインスタンス
    instances = [
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
    ]
    # GitHub ActionsではDNS解決できないことが多いのでスキップ
    return []

if __name__ == "__main__":
    print("=== Fetch start ===")
    tweets = fetch_via_fxtwitter()
    
    if not tweets:
        tweets = fetch_via_syndication()
    
    print(f"Total tweets: {len(tweets)}")
    
    # --- 0件でも番組表を空にしない ---
    prog_path = "docs/programacion.json"
    
    # パース
    by_date = {}
    for t in tweets:
        m = re.search(r'(\d{1,2}:\d{2})', t["content"])
        hora = m.group(1) if m else "19:30"
        if "vs" not in t["content"].lower() and m is None:
            continue
        title = re.sub(r'https?://\S+|#\S+', '', t["content"]).strip()[:120]
        dt = datetime.datetime.now(PYT)
        fecha = dt.strftime("%Y-%m-%d")
        by_date.setdefault(fecha, []).append({
            "hora_pyt": hora,
            "titulo": title,
            "en_vivo": True,
            "canal": "【entity-Tigo Sports¦canonical_name=Tigo Sports】",
            "fecha_pyt": fecha,
            "url_x": t["url"]
        })
    
    if len(tweets) == 0:
        print("No tweets found - keeping old file if exists")
        if os.path.exists(prog_path):
            # 古いファイルを維持して終了 (0件で上書きしない)
            with open(prog_path,"r",encoding="utf-8") as f:
                old = json.load(f)
            # 更新日だけ変える
            old["fecha_actualizacion"] = datetime.datetime.now(PYT).isoformat()
            old["debug"] = "X fetch failed (403), kept old data"
            with open(prog_path,"w",encoding="utf-8") as f:
                json.dump(old, f, ensure_ascii=False, indent=2)
            print("Kept old file")
            exit(0)
        else:
            # 初回で0件ならダミーを作らない - サンプルを作る
            now = datetime.datetime.now(PYT).date().isoformat()
            by_date = {now: [{"hora_pyt":"19:30","titulo":"Programación no disponible - X bloqueado (403)","en_vivo":False,"canal":"Tigo Sports","fecha_pyt":now,"url_x":""}]}
    
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
        "debug_tweets_count": len(tweets),
        "debug_note": "If 0, X is blocking. Use manual mode."
    }
    
    os.makedirs("docs", exist_ok=True)
    with open(prog_path,"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"done {len(all_progs)}")
