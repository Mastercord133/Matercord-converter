# matercord

A self-hosted YouTube converter suite running on a Raspberry Pi. Convert YouTube videos to WAV, MP3, and MP4 — no ads, no signup, no limits.

## Converters

| Route | Output | Quality |
|-------|--------|---------|
| `/wav` | Lossless WAV audio | Full quality |
| `/mp3` | Compressed MP3 audio | 192kbps |
| `/mp4` | Video | Up to 1080p |

## Stack

- **Python / Flask** — web server and API
- **yt-dlp** — YouTube downloading
- **ffmpeg** — audio/video conversion
- **Cloudflare Tunnel** — exposes the Pi to the internet without port forwarding

## Structure

```
matercord/
├── app.py          # Main app — homepage, /wav, /mp3, proxies /mp4
├── mp4.py          # Separate app for MP4 conversion (port 5011)
├── start.sh        # Start everything with one command
├── requirements.txt
└── cookies.txt     # YouTube cookies for 1080p (not committed)
```

## Setup

**1. Install system dependencies**
```bash
sudo apt install python3-venv ffmpeg -y
```

**2. Clone the repo**
```bash
git clone https://github.com/yourusername/matercord.git
cd matercord
```

**3. Start**
```bash
chmod +x start.sh
./start.sh
```

The first run creates a virtual environment and installs dependencies automatically. After that it starts instantly.

App runs on `http://localhost:5010`.

## Cookies (required for 1080p MP4)

YouTube requires authentication for high quality formats. Export cookies from your browser:

1. Install **"Get cookies.txt LOCALLY"** in Chrome
2. Go to `youtube.com` while logged in
3. Click the extension → Export → save as `cookies.txt`
4. Place `cookies.txt` in the project root

Cookies typically last 1–2 years. When they expire you'll get 403 errors — just re-export.

## Run on boot (systemd)

```bash
sudo nano /etc/systemd/system/matercord.service
```

```ini
[Unit]
Description=matercord
After=network.target

[Service]
User=aiden
WorkingDirectory=/home/aiden/matercord
ExecStart=/home/aiden/matercord/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable matercord
sudo systemctl start matercord
```

## Cloudflare Tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create matercord
```

`~/.cloudflared/config.yml`:
```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/aiden/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: matercord.com
    service: http://localhost:5010
  - service: http_status:404
```

```bash
cloudflared tunnel route dns matercord matercord.com
sudo cloudflared service install
sudo systemctl enable cloudflared
```

## Auto-update yt-dlp

YouTube regularly breaks yt-dlp. Add a weekly cron to keep it updated:

```bash
crontab -e
```

```
0 3 * * 1 /home/aiden/matercord/venv/bin/pip install -U yt-dlp -q
```

## .gitignore

Make sure `cookies.txt` is never committed:

```
venv/
__pycache__/
*.pyc
cookies.txt
```
