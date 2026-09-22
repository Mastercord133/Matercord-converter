from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)

DOWNLOAD_DIR = '/tmp/matercord'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}

# Conversion worker
def convert(job_id, url, fmt):
    jobs[job_id]['status'] = 'downloading'
    out_path = os.path.join(DOWNLOAD_DIR, f'{job_id}.{fmt}')
    cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                jobs[job_id]['pct'] = int(downloaded / total * 80)
        elif d['status'] == 'finished':
            jobs[job_id]['pct'] = 85
            jobs[job_id]['status'] = 'converting'

    base_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'{job_id}.%(ext)s'),
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'concurrent_fragment_downloads': 4,
        'extractor_args': {'youtube': {'player_client': ['android']}},
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
        },
        **(({'cookiefile': cookies_path}) if os.path.exists(cookies_path) else {}),
    }
#mp4
    if fmt == 'mp4':
        ydl_opts = {
            **base_opts,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
    else:
        ydl_opts = {
            **base_opts,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': fmt,
                'preferredquality': '0' if fmt == 'wav' else '192',
            }],
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'media')
        jobs[job_id].update({'status': 'done', 'file': out_path, 'title': title, 'pct': 100})
    except Exception as e:
        jobs[job_id].update({'status': 'error', 'error': str(e)})

# â”€â”€ Long-lived cookie on every response â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.after_request
def long_cookie(resp):
    resp.set_cookie('mc', '1', max_age=365 * 24 * 60 * 60, samesite='Lax', path='/')
    return resp

# â”€â”€ Shared CSS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');
:root{--bg:#111110;--card:#1a1a18;--card-hover:#1f1f1d;--border:#2a2a27;--accent:#c8f135;--text:#e8e8e0;--muted:#666660;--mono:'Space Mono',monospace;--sans:'Syne',sans-serif;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;}
header{display:flex;align-items:center;justify-content:space-between;padding:28px 48px;border-bottom:1px solid var(--border);}
.logo{font-family:var(--mono);font-size:18px;color:var(--text);text-decoration:none;}
.logo span{color:var(--accent);}
nav{display:flex;gap:32px;}
nav a{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);text-decoration:none;transition:color .2s;}
nav a:hover{color:var(--text);}nav a.active{color:var(--accent);}
footer{border-top:1px solid var(--border);padding:32px 48px;display:flex;align-items:center;justify-content:space-between;font-family:var(--mono);font-size:11px;color:var(--muted);}
@media(max-width:640px){header{padding:20px 24px;}nav{display:none;}footer{padding:24px;flex-direction:column;gap:8px;}}
"""

def shell(title, body, active='', extra=''):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} â€” matercord</title>
<style>{STYLE}{extra}</style>
</head>
<body>
<header>
  <a href="/" class="logo">mater<span>cord</span></a>
  <nav>
    <a href="/wav" class="{'active' if active=='wav' else ''}">wav</a>
    <a href="/mp3" class="{'active' if active=='mp3' else ''}">mp3</a>
    <a href="/mp4" class="{'active' if active=='mp4' else ''}">mp4</a>
  </nav>
</header>
{body}
<footer><span>Â© 2025 matercord</span><span>powered by pi</span></footer>
</body></html>"""

# â”€â”€ Homepage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/')
def home():
    body = """
<section style="padding:80px 48px 48px;max-width:900px">
  <p style="font-family:var(--mono);font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);margin-bottom:20px">// free online tools</p>
  <h1 style="font-size:clamp(42px,7vw,80px);font-weight:800;line-height:.95;letter-spacing:-.04em;margin-bottom:24px">Convert<br><em style="font-style:normal;color:var(--accent)">anything.</em></h1>
  <p style="font-family:var(--mono);font-size:13px;color:var(--muted);line-height:1.7;max-width:480px">Fast, free media converters. No signup. No watermarks. Paste a link and go.</p>
</section>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:2px;padding:0 48px 80px">
  <a href="/wav" class="hcard" style="--ca:#c8f135">
    <span class="badge" style="color:#c8f135;background:rgba(200,241,53,.1)">&#9679; Live</span>
    <div class="ctitle"><span>yt</span><span class="arr">â†’</span><span style="color:#c8f135">wav</span></div>
    <p class="cdesc">Extract lossless WAV audio from any YouTube video.</p>
    <div class="cfoot"><span class="curl">matercord.com/wav</span><span class="carrow" style="background:rgba(200,241,53,.15);color:#c8f135">â†—</span></div>
  </a>
  <a href="/mp3" class="hcard" style="--ca:#f1d035">
    <span class="badge" style="color:#f1d035;background:rgba(241,208,53,.1)">&#9679; Live</span>
    <div class="ctitle"><span>yt</span><span class="arr">â†’</span><span style="color:#f1d035">mp3</span></div>
    <p class="cdesc">Convert YouTube to high-quality MP3. 192kbps, download instantly.</p>
    <div class="cfoot"><span class="curl">matercord.com/mp3</span><span class="carrow" style="background:rgba(241,208,53,.15);color:#f1d035">â†—</span></div>
  </a>
  <a href="/mp4" class="hcard" style="--ca:#35c8f1">
    <span class="badge" style="color:#35c8f1;background:rgba(53,200,241,.1)">&#9679; Live</span>
    <div class="ctitle"><span>yt</span><span class="arr">â†’</span><span style="color:#35c8f1">mp4</span></div>
    <p class="cdesc">Download YouTube videos as MP4. Best available quality.</p>
    <div class="cfoot"><span class="curl">matercord.com/mp4</span><span class="carrow" style="background:rgba(53,200,241,.15);color:#35c8f1">â†—</span></div>
  </a>
</div>"""
    extra = """
.hcard{background:var(--card);border:1px solid var(--border);border-radius:4px;padding:32px 28px 28px;text-decoration:none;color:inherit;display:flex;flex-direction:column;gap:16px;position:relative;overflow:hidden;transition:background .25s,transform .25s;}
.hcard::after{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--ca);transform:scaleX(0);transform-origin:left;transition:transform .3s;}
.hcard:hover{background:var(--card-hover);transform:translateY(-2px)}.hcard:hover::after{transform:scaleX(1)}
.badge{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;padding:4px 10px;border-radius:2px;width:fit-content}
.ctitle{font-size:32px;font-weight:800;letter-spacing:-.04em;font-family:var(--mono)}.arr{color:var(--muted);margin:0 4px;font-weight:400}
.cdesc{font-family:var(--mono);font-size:11px;color:var(--muted);line-height:1.7;flex:1}
.cfoot{display:flex;align-items:center;justify-content:space-between;padding-top:16px;border-top:1px solid var(--border);margin-top:auto}
.curl{font-family:var(--mono);font-size:10px;color:var(--muted)}
.carrow{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;transition:transform .2s}
.hcard:hover .carrow{transform:rotate(45deg)}
@media(max-width:640px){section,div[style*="padding:0 48px"]{padding-left:24px!important;padding-right:24px!important}}"""
    return shell('matercord', body, extra=extra)

# â”€â”€ Converter page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CONVERTER_EXTRA = """
.wrap{display:flex;align-items:center;justify-content:center;min-height:calc(100vh - 200px);padding:40px 24px;}
.box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:48px 40px 40px;width:100%;max-width:560px;}
.box h1{font-family:var(--mono);font-size:40px;font-weight:700;letter-spacing:-.04em;margin-bottom:6px;}
.box .sub{font-family:var(--mono);font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--muted);margin-bottom:36px;}
.row{display:flex;gap:12px;margin-bottom:24px;}
input[type=text]{flex:1;background:#0d0d0c;border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:var(--mono);font-size:13px;padding:14px 16px;outline:none;transition:border-color .2s;}
input[type=text]:focus{border-color:var(--accent-c);}
input[type=text]::placeholder{color:var(--muted);}
button{background:var(--accent-c);color:#111;font-family:var(--mono);font-size:13px;font-weight:700;letter-spacing:.05em;padding:14px 24px;border:none;border-radius:6px;cursor:pointer;white-space:nowrap;transition:opacity .2s;}
button:hover{opacity:.9;}button:disabled{opacity:.4;cursor:not-allowed;}
.sep{border:none;border-top:1px solid var(--border);margin:0 0 24px;}
.status-box{display:none;font-family:var(--mono);font-size:12px;}.status-box.show{display:block;}
.status-label{color:var(--muted);margin-bottom:12px;}
.bar-track{background:#0d0d0c;border-radius:4px;height:4px;overflow:hidden;margin-bottom:20px;}
.bar-fill{height:100%;background:var(--accent-c);border-radius:4px;width:0%;transition:width .4s ease;}
.dl-btn{display:none;width:100%;text-align:center;padding:14px;border-radius:6px;background:var(--accent-c);color:#111;font-family:var(--mono);font-weight:700;font-size:13px;text-decoration:none;letter-spacing:.05em;}
.dl-btn.show{display:block;}
.err{color:#f17070;margin-top:12px;display:none;font-family:var(--mono);font-size:12px;}.err.show{display:block;}
"""

def converter_page(fmt):
    accents = {'wav': '#c8f135', 'mp3': '#f1d035', 'mp4': '#35c8f1'}
    accent = accents.get(fmt, '#c8f135')
    label = fmt.upper()
    desc = 'youtube video downloader' if fmt == 'mp4' else 'youtube audio extractor'
    body = f"""
<div class="wrap">
  <div class="box">
    <h1 style="color:{accent}">yt â†’ {fmt}</h1>
    <p class="sub">{desc}</p>
    <div class="row">
      <input type="text" id="url" placeholder="https://youtube.com/watch?v=..." />
      <button id="btn" onclick="start()">Convert</button>
    </div>
    <hr class="sep">
    <div class="status-box" id="status-box">
      <p class="status-label" id="status-label">Starting...</p>
      <div class="bar-track"><div class="bar-fill" id="bar"></div></div>
    </div>
    <a class="dl-btn" id="dl-btn" href="#" download>&#8595; Download {label}</a>
    <p class="err" id="err"></p>
  </div>
</div>
<script>
const FMT='{fmt}';
let poll;
async function start(){{
  const url=document.getElementById('url').value.trim();
  if(!url)return;
  document.getElementById('btn').disabled=true;
  document.getElementById('err').className='err';
  document.getElementById('dl-btn').className='dl-btn';
  document.getElementById('status-box').className='status-box show';
  document.getElementById('status-label').textContent='Starting...';
  document.getElementById('bar').style.width='5%';
  const res=await fetch('/api/convert',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{url,fmt:FMT}})}});
  const {{job_id}}=await res.json();
  poll=setInterval(()=>check(job_id),1500);
}}
async function check(job_id){{
  const res=await fetch('/api/status/'+job_id);
  const d=await res.json();
  const label=document.getElementById('status-label');
  const bar=document.getElementById('bar');
  if(d.status==='downloading'){{label.textContent='Downloading... '+(d.pct||0)+'%';bar.style.width=(d.pct||5)+'%';}}
  else if(d.status==='converting'){{label.textContent='Converting...';bar.style.width='90%';}}
  else if(d.status==='done'){{
    clearInterval(poll);
    label.textContent='Done â€” '+(d.title||'');
    bar.style.width='100%';
    const dl=document.getElementById('dl-btn');
    dl.href='/api/download/'+job_id;
    dl.className='dl-btn show';
    document.getElementById('btn').disabled=false;
  }}else if(d.status==='error'){{
    clearInterval(poll);
    document.getElementById('status-box').className='status-box';
    const err=document.getElementById('err');
    err.textContent='Error: '+d.error;
    err.className='err show';
    document.getElementById('btn').disabled=false;
  }}
}}
</script>"""
    return shell(f'yt â†’ {fmt}', body, active=fmt,
                 extra=CONVERTER_EXTRA + f':root{{--accent-c:{accent}}}')

@app.route('/wav')
def wav(): return converter_page('wav')

@app.route('/mp3')
def mp3(): return converter_page('mp3')

@app.route('/mp4')
def mp4(): return converter_page('mp4')

# â”€â”€ API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.route('/api/convert', methods=['POST'])
def api_convert():
    data = request.get_json()
    url = data.get('url', '').strip()
    fmt = data.get('fmt', 'mp3')
    if fmt not in ('wav', 'mp3', 'mp4'):
        return jsonify({'error': 'invalid format'}), 400
    if not url:
        return jsonify({'error': 'no url'}), 400
    job_id = str(uuid.uuid4())
    jobs[job_id] = {'status': 'queued', 'pct': 0, 'created': time.time()}
    threading.Thread(target=convert, args=(job_id, url, fmt), daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/api/status/<job_id>')
def api_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'status': 'error', 'error': 'job not found'}), 404
    return jsonify({k: v for k, v in job.items() if k != 'file'})

@app.route('/api/download/<job_id>')
def api_download(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        return 'Not ready', 404
    filepath = job['file']
    if not os.path.exists(filepath):
        return 'File gone', 404
    ext = os.path.splitext(filepath)[1]
    title = job.get('title', 'media')
    safe = "".join(c for c in title if c.isalnum() or c in ' -_').strip()
    resp = send_file(filepath, as_attachment=True, download_name=f'{safe}{ext}')
    @resp.call_on_close
    def cleanup():
        try:
            os.remove(filepath)
            jobs.pop(job_id, None)
        except Exception:
            pass
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010, debug=False)
