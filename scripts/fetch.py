import re, json, datetime, zoneinfo, os, requests, time
from bs4 import BeautifulSoup

PYT = zoneinfo.ZoneInfo("America/Asuncion")

# Nitterインスタンス (snscrape 403の時のフォールバック)
NITTERS = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.net",
    "https://nitter.1d4.us"
]

def fetch_via_snscrape():
    try:
        import snscrape.modules.twitter as sntwitter
        tweets = []
        for i, tw in enumerate(sntwitter.TwitterUserScraper("TigoSportsPY").get_items()):
            if i >= 100: break
            txt = tw.rawContent
            if "vs" in txt.lower() or "en vivo" in txt.lower():
                tweets.append({
                    "date": tw.date.astimezone(PYT).isoformat(),
                    "content": txt,
                    "url": tw.url
                })
        if tweets:
            print(f"snscrape success: {len(tweets)}")
            return tweets
    except Exception as e:
        print(f"snscrape failed: {e}")
    return []

def fetch_via_nitter():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for base in NITTERS:
        try:
            url = f"{base}/TigoSportsPY"
            print(f"Trying {url}")
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code != 200:
                print(f"{base} status {r.status_code}")
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            tweets = []
            for item in soup.select(".timeline-item")[:50]:
                content_el = item.select_one(".tweet-content")
                if not content_el: continue
                txt = content_el.get_text(" ", strip=True)
                if "vs" not in txt.lower() and "en vivo" not in txt.lower(): continue
                date_el = item.select_one(".tweet-date a")
                link = date_el["href"] if date_el else ""
                full_url = f"https://twitter.com{link}" if link else f"{base}/TigoSportsPY"
                # 日付は今の日付で代用 (Nitterの時間はパースが不安定)
                tweets.append({
                    "date": datetime.datetime.now(PYT).isoformat(),
                    "content": txt,
                    "url": full_url
                })
            if tweets:
                print(f"Nitter {base} success: {len(tweets)}")
                return tweets
        except Exception as e:
            print(f"Nitter {base} failed: {e}")
            time.sleep(1)
            continue
    return []

def to_programacion(tweets):
    by_date = {}
    for t in tweets:
        try:
            dt = datetime.datetime.fromisoformat(t["date"])
        except:
            dt = datetime.datetime.now(PYT)
        fecha = dt.strftime("%Y-%m-%d")
        m = re.search(r'(\d{1,2}:\d{2})', t["content"])
        if not m: 
            # 時間がない投稿は 19:30 と仮置きしない -> スキップ
            # ただしタイトルにvsがあれば時間なしでも入れる
            if "vs" not in t["content"].lower():
                continue
            hora = "19:30"
        else:
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
    tweets = fetch_via_snscrape()
    if not tweets:
        print("snscrape 403 -> fallback to Nitter")
        tweets = fetch_via_nitter()
    
    print(f"Total tweets: {len(tweets)}")
    by_date = to_programacion(tweets)
    
    now = datetime.datetime.now(PYT).date()
    for i in range(-2,5):
        d = (now + datetime.timedelta(days=i)).isoformat()
        by_date.setdefault(d, [])
    
    # Xが0件でも空ファイルを作らないように、最後の成功データを保持
    prog_path = "docs/programacion.json"
    if len(tweets) == 0 and os.path.exists(prog_path):
        print("No new tweets, keep old file")
        # 古いファイルを維持
        exit(0)
    
    all_progs = []
    for d in sorted(by_date.keys()):
        all_progs.extend(by_date[d])

    out = {
        "fecha_actualizacion": datetime.datetime.now(PYT).isoformat(),
        "fuente": "X @TigoSportsPY via snscrape+nitter fallback",
        "fechas_disponibles": sorted(by_date.keys()),
        "programacion_por_fecha": {d: {"fecha": d, "programacion": by_date[d]} for d in sorted(by_date.keys())},
        "programacion": by_date.get(now.isoformat(), []),
        "epg": [{"start_pyt": f"{p['fecha_pyt']} {p['hora_pyt']}", "title": p["titulo"], "live": p["en_vivo"]} for p in all_progs],
        "debug_tweets_count": len(tweets)
    }
    
    os.makedirs("docs", exist_ok=True)
    with open(prog_path,"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"done {len(all_progs)} programs")
