import requests, os, datetime, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Paraguay 公式URL候補（存在するものだけミラーする）
OFFICIAL_URLS = [
    "https://www.tigosports.com.py/",
    "https://www.tigosports.com.py/programacion",
    "https://www.tigosports.com.py/en-vivo",
    "https://app.tigosports.com.py/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-PY,es;q=0.9",
}

def download_official():
    os.makedirs("docs/mirror", exist_ok=True)
    os.makedirs("docs/data", exist_ok=True)
    
    saved = []
    for url in OFFICIAL_URLS:
        try:
            print(f"Descargando {url}...")
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                print(f"  -> {r.status_code} skip")
                continue
            
            soup = BeautifulSoup(r.text, "lxml")
            
            # 全リンクを絶対URLに変換（Pagesでも切れないように）
            for tag in soup.find_all(['a','img','link','script']):
                attr = 'href' if tag.name in ['a','link'] else 'src'
                if tag.has_attr(attr):
                    val = tag[attr]
                    if val.startswith('/'):
                        tag[attr] = urljoin(url, val)
            
            # JST/GMT変換バナーを注入
            banner = soup.new_tag("div")
            banner['style'] = "background:#00a9e0;color:#00111a;padding:10px 16px;font-family:monospace;font-size:12px;position:sticky;top:0;z-index:9999;display:flex;gap:12px;align-items:center;flex-wrap:wrap"
            banner.append(BeautifulSoup("""
                <strong>Mirror: 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Oficial</strong>
                <span id="tz-info">PYT UTC-3</span>
                <select id="tz-select" style="padding:4px 8px;border-radius:999px">
                  <option value="America/Asuncion" selected>PYT Asuncion</option>
                  <option value="UTC">GMT/UTC</option>
                  <option value="Asia/Tokyo">JST Tokyo (+1d)</option>
                </select>
                <span style="font-size:10px">Actualizado: """+datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")+"""</span>
                <a href="../index.html" style="margin-left:auto;background:#000;color:#fff;padding:4px 10px;border-radius:999px;text-decoration:none">Ver Guía EPG</a>
            """, "html.parser"))
            
            if soup.body:
                soup.body.insert(0, banner)
                
                # 日付付きタイムゾーン変換スクリプトを注入
                script = soup.new_tag("script")
                script.string = """
                function getOff(tz,d){try{const f=new Intl.DateTimeFormat('en-US',{timeZone:tz,timeZoneName:'shortOffset',hour:'2-digit'});const n=f.formatToParts(d).find(p=>p.type==='timeZoneName')?.value||'GMT+0';const m=n.match(/GMT([+-])(\\d+)(?::(\\d+))?/);return m?(m[1]==='+'?1:-1)*(parseInt(m[2])*60+parseInt(m[3]||'0')):0}catch{return 0}}
                document.getElementById('tz-select')?.addEventListener('change',e=>{
                  const target=e.target.value;
                  document.querySelectorAll('*').forEach(el=>{
                    const txt=el.childNodes[0]?.nodeValue;
                    if(!txt) return;
                    const m=txt.match(/(\\d{1,2}:\\d{2})/);
                    if(!m) return;
                    // 簡易変換表示
                    const span=document.createElement('span');
                    span.style.cssText='font-size:10px;color:#00a9e0;margin-left:6px';
                    const now=new Date();
                    const diff=getOff(target,now)-getOff('America/Asuncion',now);
                    let total=parseInt(m[1].split(':')[0])*60+parseInt(m[1].split(':')[1])+diff;
                    let shift=0;
                    while(total<0){total+=1440;shift--;} while(total>=1440){total-=1440;shift++;}
                    const h=String(Math.floor(total/60)).padStart(2,'0'), mm=String(total%60).padStart(2,'0');
                    span.textContent=`→ ${h}:${mm} ${target} ${shift!==0?(shift>0?`(+${shift}d)`:`(${shift}d)`):''}`;
                    if(!el.querySelector('.tz-converted')){span.className='tz-converted';el.appendChild(span);}
                  });
                });
                """
                soup.body.append(script)
            
            # 保存
            filename = url.replace("https://","").replace("http://","").replace("/","_").replace(".","_") + ".html"
            if filename.endswith("_.html"):
                filename = filename[:-6] + ".html"
            path = f"docs/mirror/{filename}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            saved.append(path)
            print(f"  -> Saved {path} ({len(str(soup))} bytes)")
            
        except Exception as e:
            print(f"[ERROR] {url}: {e}")
    
    # メインの index.html をミラー一覧 + EPGへのリンクに
    index_html = f"""
    <!DOCTYPE html>
    <html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>【entity-Tigo Sports¦canonical_name=Tigo Sports】 - Mirror Oficial</title>
    <style>body{{background:#0a0e1a;color:#e6eefc;font-family:system-ui;padding:20px}} a{{color:#00a9e0}} .card{{border:1px solid #23344f;background:#1a2332;border-radius:12px;padding:16px;margin:12px 0}}</style>
    </head><body>
    <h1> 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Paraguay - Mirror Oficial</h1>
    <p>Actualizado: {datetime.datetime.utcnow().isoformat()}Z - Descarga directa del sitio oficial</p>
    <div class="card"><h3>Guía EPG con conversión de fecha (+1d)</h3><a href="./index_epg.html">Ver Guía TV estilo televisor →</a></div>
    <h3>Paginas espejo:</h3>
    {''.join(f'<div class="card"><a href="./mirror/{os.path.basename(s)}" target="_blank">{s}</a></div>' for s in saved)}
    <p style="font-size:11px;color:#8aa0c2">Este sitio es un mirror para visualización en GitHub Pages. Todo el contenido pertenece a 【entity-Tigo Sports¦canonical_name=Tigo Sports】 Paraguay.</p>
    </body></html>
    """
    # EPGは別名で保存し、メインindexはミラー案内に
    if os.path.exists("docs/index.html"):
        os.rename("docs/index.html", "docs/index_epg.html")
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    
    print(f"Done: {len(saved)} mirrors")

if __name__ == "__main__":
    download_official()
