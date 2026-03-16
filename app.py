# app.py - Render.com icin Vavoo Proxy
from flask import Flask, request, Response, redirect, jsonify
import requests
import json
import logging
import os
import time
import random

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VAVOO_API = "https://vavoo.to/mediahubmx-resolve.json"

# Token cache
_sig_cache = {"token": None, "time": 0}

def get_signature():
    """Lokke signature al - 1 saat cache"""
    now = time.time()
    if _sig_cache["token"] and (now - _sig_cache["time"]) < 3600:
        return _sig_cache["token"]
    try:
        data = {
            "token": "", "reason": "boot", "locale": "de", "theme": "dark",
            "metadata": {
                "device": {"type": "desktop", "uniqueId": ""},
                "os": {"name": "win32", "version": "Windows 10", "abis": ["x64"], "host": "DESKTOP"},
                "app": {"platform": "electron"},
                "version": {"package": "app.lokke.main", "binary": "1.0.19", "js": "1.0.19"}
            },
            "appFocusTime": 173, "playerActive": False, "playDuration": 0,
            "devMode": True, "hasAddon": True, "castConnected": False,
            "package": "app.lokke.main", "version": "1.0.19", "process": "app",
            "firstAppStart": int(now*1000)-10000, "lastAppStart": int(now*1000)-10000,
            "ipLocation": 0, "adblockEnabled": True,
            "proxy": {"supported": ["ss"], "engine": "cu", "enabled": False, "autoServer": True, "id": 0},
            "iap": {"supported": False}
        }
        resp = requests.post(
            "https://www.lokke.app/api/app/ping",
            json=data,
            headers={"user-agent": "okhttp/4.11.0", "content-type": "application/json"},
            timeout=10
        )
        token = resp.json().get("addonSig")
        if token:
            _sig_cache["token"] = token
            _sig_cache["time"] = now
            app.logger.info(f"Token alindi: {token[:20]}...")
            return token
    except Exception as e:
        app.logger.error(f"Token hatasi: {e}")
    return None

def resolve_url(vavoo_url):
    """URL'yi resolve et - once token ile, olmazsa token'siz"""
    
    def do_resolve(sig=None):
        headers = {
            "User-Agent": "MediaHubMX/2",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if sig:
            headers["mediahubmx-signature"] = sig
        
        payload = {
            "language": "tr",
            "region": "TR",
            "url": vavoo_url,
            "clientVersion": "3.0.3"
        }
        resp = requests.post(VAVOO_API, json=payload, headers=headers, timeout=15)
        app.logger.info(f"API status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0 and "url" in data[0]:
                return data[0]["url"]
            elif isinstance(data, dict):
                return data.get("url") or data.get("streamUrl")
        return None

    # 1. Lokke token ile dene
    sig = get_signature()
    real_url = do_resolve(sig)
    if real_url:
        return real_url

    # 2. Token'siz dene (yerelde calisiyordu)
    app.logger.info("Token ile olmadi, token'siz deneniyor...")
    real_url = do_resolve(None)
    return real_url

@app.route('/')
def index():
    return "<h1>Vavoo Proxy</h1><p>Kullanim: /m3u?url=VAVOO_LINKI</p>"

@app.route('/m3u')
def m3u_proxy():
    url = request.args.get('url')
    if not url:
        return "URL gerekli", 400

    app.logger.info(f"Cozuluyor: {url}")
    real_url = resolve_url(url)

    if real_url:
        app.logger.info(f"Gercek link: {real_url}")
        return redirect(real_url, code=302)
    
    return jsonify({"error": "cozumlenemedi", "url": url}), 502

@app.route('/resolve')
def resolve():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL gerekli"}), 400
    real_url = resolve_url(url)
    if real_url:
        return jsonify({"streamUrl": real_url})
    return jsonify({"error": "cozumlenemedi"}), 502

@app.route('/turkey.m3u')
def turkey_playlist():
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    base = f"{scheme}://{request.host}"
    
    channels = [
        ("TRT 1 HD", "1221669131f90e763b2bbf"),
        ("ATV HD", "1332310706d6138ade7950"),
        ("KANAL D HD", "113044193323e36b85a648"),
        ("SHOW TV HD", "8795889605c7795ac9528"),
        ("STAR TV HD", "219297129315c074c03f8e"),
        ("FOX TV HD", "15614953198c1780c4df07"),
        ("TV8 HD", "1702470161fe0c4007a0bb"),
        ("BEYAZ TV HD", "805689873341639546753"),
        ("NTV HD", "2073292907cc209d200015"),
        ("CNN TURK HD", "2056768647bd7eb3f3cf70"),
        ("HABERTURK HD", "11966263871c480a66a299"),
        ("A HABER HD", "535272601f07c2fbd1f2b"),
        ("TRT HABER HD", "6036516388b222edb706e"),
        ("A SPOR HD", "2556711030587eed1d7123"),
        ("TRT SPOR HD", "22629699381f94fcd9dbe6"),
        ("S SPORT HD", "21232735984a3f0b463d66"),
        ("BEIN SPORTS 1 HD", "66217962033a2d3e9c47f"),
        ("BEIN SPORTS 2 HD", "28515391437e928cafd5dd"),
        ("BEIN SPORTS 3 HD", "17005958018c5d23b49ef0"),
        ("TRT COCUK HD", "30291805064bacb8a4036d"),
        ("CARTOON NETWORK", "327818589842dbaee1327c"),
        ("DISNEY CHANNEL HD", "3578544716a4cc42d03dcd"),
        ("TRT MUZIK", "970382162286220f5fa39"),
        ("TEVE2 HD", "1917502631a9b6866e12b6"),
        ("KANAL 7 HD", "109266795988e12fc489b6"),
        ("TRT 2 HD", "38843190334c7e81c1c6fc"),
        ("HALK TV", "1320391955e6c5bb1bedb6"),
        ("24 HABER HD", "3828793616b62b9cc5834c"),
    ]
    
    lines = ["#EXTM3U\n"]
    for name, id in channels:
        lines.append(f'#EXTINF:-1 group-title="Turkey",{name}\n')
        lines.append(f'#EXTVLCOPT:http-user-agent=VAVOO/2.6\n')
        lines.append(f'{base}/m3u?url=https://vavoo.to/vavoo-iptv/play/{id}\n')
    
    return Response(''.join(lines), mimetype='audio/x-mpegurl')

@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
