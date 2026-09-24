from flask import Flask, request, jsonify, send_file, Response
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)

DOWNLOAD_DIR = '/tmp/matercord'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}

def convert(job_id, url):
    jobs[job_id]['status'] = 'downloading'
    out_path = os.path.join(DOWNLOAD_DIR, f'{job_id}.mp4')
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

    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, f'{job_id}.%(ext)s'),
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'concurrent_fragment_downloads': 4,
        'format': 'bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
        **(({'cookiefile': cookies_path}) if os.path.exists(cookies_path) else {}),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
        jobs[job_id].update({'status': 'done', 'file': out_path, 'title': title, 'pct': 100})
    except Exception as e:
        jobs[job_id].update({'status': 'error', 'error': str(e)})

@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>yt → mp4 — matercord</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');
:root{--bg:#111110;--card:#1a1a18;--border:#2a2a27;--accent:#35c8f1;--text:#e8e8e0;--muted:#666660;--mono:'Space Mono',monospace;--sans:'Syne',sans-serif;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;}
header{display:flex;align-items:center;justify-content:space-between;padding:28px 48px;border-bottom:1px solid var(--border);}
.logo{font-family:var(--mono);font-size:18px;color:var(--text);text-decoration:none;}
.logo span{color:#c8f135;}
nav{display:flex;gap:32px;}
nav a{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);text-decoration:none;}
nav a:hover{color:var(--text);}nav a.active{color:var(--accent);}
footer{border-top:1px solid var(--border);padding:32px 48px;display:flex;align-items:center;justify-content:space-between;font-family:var(--mono);font-size:11px;color:var(--muted);}
.wrap{display:flex;align-items:center;justify-content:center;min-height:calc(100vh - 200px);padding:40px 24px;}
.box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:48px 40px 40px;width:100%;max-width:560px;}
.box h1{font-family:var(--mono);font-size:40px;font-weight:700;letter-spacing:-.04em;margin-bottom:6px;color:var(--accent);}
.sub{font-family:var(--mono);font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--muted);margin-bottom:36px;}
.row{display:flex;gap:12px;margin-bottom:24px;}
input{flex:1;background:#0d0d0c;border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:var(--mono);font-size:13px;padding:14px 16px;outline:none;}
input:focus{border-color:var(--accent);}input::placeholder{color:var(--muted);}
button{background:var(--accent);color:#111;font-family:var(--mono);font-size:13px;font-weight:700;padding:14px 24px;border:none;border-radius:6px;cursor:pointer;}
button:disabled{opacity:.4;cursor:not-allowed;}
.sep{border:none;border-top:1px solid var(--border);margin:0 0 24px;}
.status-box{display:none;font-family:var(--mono);font-size:12px;}.status-box.show{display:block;}
.status-label{color:var(--muted);margin-bottom:12px;}
.bar-track{background:#0d0d0c;border-radius:4px;height:4px;overflow:hidden;margin-bottom:20px;}
.bar-fill{height:100%;background:var(--accent);border-radius:4px;width:0%;transition:width .4s;}
.dl-btn{display:none;width:100%;text-align:center;padding:14px;border-radius:6px;background:var(--accent);color:#111;font-family:var(--mono);font-weight:700;font-size:13px;text-decoration:none;}
.dl-btn.show{display:block;}
.err{color:#f17070;margin-top:12px;display:none;font-family:var(--mono);font-size:12px;}.err.show{display:block;}
@media(max-width:640px){header{padding:20px 24px;}nav{display:none;}footer{padding:24px;}}
</style>
</head>
<body>
<header>
  <a href="/" class="logo">mater<span>cord</span></a>
  <nav>
    <a href="/wav">wav</a>
    <a href="/mp3">mp3</a>
    <a href="/mp4" class="active">mp4</a>
  </nav>
</header>
<div class="wrap">
  <div class="box">
    <h1>yt → mp4</h1>
    <p class="sub">youtube video downloader</p>
    <div class="row">
      <input type="text" id="url" placeholder="https://youtube.com/watch?v=..." />
      <button id="btn" onclick="start()">Convert</button>
    </div>
    <hr class="sep">
    <div class="status-box" id="status-box">
      <p class="status-label" id="status-label">Starting...</p>
      <div class="bar-track"><div class="bar-fill" id="bar"></div></div>
    </div>
    <a class="dl-btn" id="dl-btn" href="#" download>&#8595; Download MP4</a>
    <p class="err" id="err"></p>
  </div>
</div>
<footer><span>© 2025 matercord</span><span>powered by pi</span></footer>
<script>
let poll;
async function start(){
  const url=document.getElementById('url').value.trim();
  if(!url)return;
  document.getElementById('btn').disabled=true;
  document.getElementById('err').className='err';
  document.getElementById('dl-btn').className='dl-btn';
  document.getElementById('status-box').className='status-box show';
  document.getElementById('status-label').textContent='Starting...';
  document.getElementById('bar').style.width='5%';
  const res=await fetch('/mp4/api/convert',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
  const {job_id}=await res.json();
  poll=setInterval(()=>check(job_id),1500);
}
async function check(job_id){
  const res=await fetch('/mp4/api/status/'+job_id);
  const d=await res.json();
  const label=document.getElementById('status-label');
  const bar=document.getElementById('bar');
  if(d.status==='downloading'){label.textContent='Downloading... '+(d.pct||0)+'%';bar.style.width=(d.pct||5)+'%';}
  else if(d.status==='converting'){label.textContent='Converting...';bar.style.width='90%';}
  else if(d.status==='done'){
    clearInterval(poll);
    label.textContent='Done — '+(d.title||'');
    bar.style.width='100%';
    const dl=document.getElementById('dl-btn');
    dl.href='/mp4/api/download/'+job_id;
    dl.className='dl-btn show';
    document.getElementById('btn').disabled=false;
  }else if(d.status==='error'){
    clearInterval(poll);
    document.getElementById('status-box').className='status-box';
    const err=document.getElementById('err');
    err.textContent='Error: '+d.error;
    err.className='err show';
    document.getElementById('btn').disabled=false;
  }
}
</script>
</body></html>"""

@app.route('/api/convert', methods=['POST'])
def api_convert():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'no url'}), 400
    job_id = str(uuid.uuid4())
    jobs[job_id] = {'status': 'queued', 'pct': 0, 'created': time.time()}
    threading.Thread(target=convert, args=(job_id, url), daemon=True).start()
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
    title = job.get('title', 'video')
    safe = "".join(c for c in title if c.isalnum() or c in ' -_').strip()
    resp = send_file(filepath, as_attachment=True, download_name=f'{safe}.mp4')
    @resp.call_on_close
    def cleanup():
        try:
            os.remove(filepath)
            jobs.pop(job_id, None)
        except Exception:
            pass
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5011, debug=False)
