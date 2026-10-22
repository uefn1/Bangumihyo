import requests, os, datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

OFFICIAL_URLS = [
    "https://www.tigosports.com.py/",
    "https://www.tigosports.com.py/programacion",
    "https://app.tigosports.com.py/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-PY,es;q=0.9",
}

def download_official():
    os.makedirs("docs/mirror", exist_ok=True)
    saved = []
    
    for url in OFFICIAL_URLS:
        try:
            print(f"Downloading {url}")
            r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            if r.status_code != 200:
                print(f"  {r.status_code} skip")
                continue
            
            soup = BeautifulSoup(r.text, "lxml")
            
            # 修正: <base>タグを追加して相対パスを解決
            head = soup.head
            if head:
                base = soup.new_tag("base", href=url)
                head.insert(0, base)
                
                # Pages用のviewportとcharsetを保証
                if not soup.find("meta", charset=True):
                    meta = soup.new_tag("meta", charset="UTF-8")
                    head.insert(1, meta)
            
            # GitHub Pages用のJST変換バナーを注入
            banner_html = f"""
            <div id="tigo-mirror-banner" style="background:#00a9e0;color:#00111a;padding:10px 16px;font-family:system-ui,sans-serif;font-size:12px;position:sticky;top:0;z-index:99999;display:flex;gap:12px;align-items:center;flex-wrap:wrap;border-bottom:2px solid #000">
              <strong>MIRROR: {url}</strong>
              <span>Actualizado: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</span>
              <select id="tz-select" style="padding:4px 10px;border-radius:999px;border:1px solid #000">
                <option value="America/Asuncion" selected>PYT UTC-3</option>
                <option value="UTC">GMT</option>
                <option value="Asia/Tokyo">JST Tokyo (+1d)</option>
              </select>
              <span id="tz-info" style="font-size:10px"></span>
              <a href="../" style="margin-left:auto;background:#000;color:#fff;padding:5px 12px;border-radius:999px;text-decoration:none">← Volver</a>
              <a href="../index_epg.html" style="background:#fff;color:#000;padding:5px 12px;border-radius:999px;text-decoration:none">Guía EPG TV</a>
            </div>
            <script>
            (function(){{
              function getOff(tz,d){{
                try{{
                  const f=new Intl.DateTimeFormat('en-US',{{timeZone:tz,timeZoneName:'shortOffset',hour:'2-digit'}});
                  const n=f.formatToParts(d).find(p=>p.type==='timeZoneName')?.value||'GMT+0';
                  const m=n.match(/GMT([+-])(\\d+)(?::(\\d+))?/);
                  return m?(m[1]==='+'?1:-1)*(parseInt(m[2])*60+parseInt(m[3]||'0')):0;
                }}catch{{return 0}}
              }}
              const sel=document.getElementById('tz-select');
              sel&&sel.addEventListener('change',e=>{{
                const target=e.target.value;
                const now=new Date();
                const diff=getOff(target,now)-getOff('America/Asuncion',now);
                document.getElementById('tz-info').textContent=`差分 ${{diff/60}}時間`;
                // 時刻っぽい要素に変換バッジを追加
                document.querySelectorAll('time, [class*="hora"], [class*="time"]').forEach(el=>{{
                  if(el.dataset.tzDone) return;
                  const m=el.textContent.match(/(\\d{{1,2}}:\\d{{2}})/);
                  if(!m) return;
                  let total=parseInt(m[1].split(':')[0])*60+parseInt(m[1].split(':')[1])+diff;
                  let shift=0;
                  while(total<0){{total+=1440;shift--;}}
                  while(total>=1440){{total-=1440;shift++;}}
                  const h=String(Math.floor(total/60)).padStart(2,'0'), mm=String(total%60).padStart(2,'0');
                  const badge=document.createElement('span');
                  badge.style.cssText='font-size:10px;color:#00a9e0;background:#00111a;padding:1px 5px;border-radius:999px;margin-left:6px';
                  badge.textContent=`→ ${{h}}:${{mm}} ${{target}} ${{shift?`(${{shift>0?'+':''}}${{shift}}d)`:''}}`;
                  el.appendChild(badge);
                  el.dataset.tzDone='1';
                }});
              }});
            }})();
            </script>
            """
            banner = BeautifulSoup(banner_html, "html.parser")
            if soup.body:
                soup.body.insert(0, banner)
            
            # CSPやX-Frameを削除（Pagesで表示できるように）
            for meta in soup.find_all("meta", {"http-equiv": True}):
                if meta.get("http-equiv", "").lower() in ["content-security-policy", "x-frame-options"]:
                    meta.decompose()
            
            filename = url.replace("https://","").replace("/","_").replace(".","_").strip("_") + ".html"
            path = f"docs/mirror/{filename}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            saved.append(filename)
            print(f"  Saved {path}")
            
        except Exception as e:
            print(f"[ERROR] {url}: {e}")
            import traceback; traceback.print_exc()
    
    print(f"Done {len(saved)} files")
    return saved

if __name__ == "__main__":
    download_official()
