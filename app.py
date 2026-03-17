import os
from flask import Flask, request, Response, redirect
import requests
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VAVOO_API = "https://vavoo.to/mediahubmx-resolve.json"

@app.route('/')
def index():
    return "Service is running."

@app.route('/m3u')
def m3u_proxy():
    url = request.args.get('url')
    if not url:
        return "URL required", 400
    
    payload = {
        "language": "tr",
        "region": "TR",
        "url": url,
        "clientVersion": "3.0.3"
    }
    
    headers = {
        "User-Agent": "MediaHubMX/2",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        resp = requests.post(VAVOO_API, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # Farklı yanıt formatlarını kontrol et
            if isinstance(data, list) and len(data) > 0:
                real_url = data[0].get("url")
            else:
                real_url = data.get("streamUrl") or data.get("url")
            
            if real_url:
                return redirect(real_url, code=302)
        return "API Error", 500
    except Exception as e:
        return f"Proxy Error: {str(e)}", 500

@app.route('/vavoo_full.m3u')
def vavoo_full():
    base_url = request.host_url
    try:
        # Bu dosyanın aynı klasörde olması şart!
        with open('vavoo_Turkey.m3u', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return "vavoo_Turkey.m3u file not found", 404
    
    new_lines = ["#EXTM3U\n"]
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF'):
            new_lines.append(line + '\n')
        elif line.startswith('http') and 'vavoo.to' in line:
            # Buradaki sihirli dokunuş: Local IP yerine Render linkini basar
            proxy_url = f"{base_url}m3u?url={line}\n"
            new_lines.append(proxy_url)
    
    return Response(''.join(new_lines), mimetype='audio/x-mpegurl')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
