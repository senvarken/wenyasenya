import os
from flask import Flask, request, Response, redirect
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VAVOO_API = "https://vavoo.to/mediahubmx-resolve.json"

@app.route('/')
def index():
    return "System Online"

@app.route('/m3u')
def m3u_proxy():
    url = request.args.get('url')
    if not url:
        return "URL missing", 400
    
    # Forumdaki yeni sistem: POST isteği ile gerçek linki alıyoruz
    payload = {
        "language": "tr",
        "region": "TR",
        "url": url,
        "clientVersion": "3.0.3"
    }
    
    headers = {
        "User-Agent": "MediaHubMX/2",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(VAVOO_API, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            
            # Linki ayıkla
            real_url = None
            if isinstance(data, list) and len(data) > 0:
                real_url = data[0].get("url")
            elif isinstance(data, dict):
                real_url = data.get("url") or data.get("streamUrl")

            if real_url:
                # KRİTİK NOKTA: Bazı oynatıcılar User-Agent gönderemez. 
                # Eğer VLC veya Televizo kullanıyorsan, bu yönlendirme linkine 
                # User-Agent parametresi eklemek işi sağlama alır.
                if "|" not in real_url:
                    # Birçok IPTV oynatıcısı linkin sonuna | ekleyince User-Agent olarak algılar
                    real_url = f"{real_url}|User-Agent=libmpv"
                
                return redirect(real_url, code=302)
        
        return "API Error", 500
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/list.m3u')
def get_list():
    base_url = request.host_url
    try:
        with open('vavoo_Turkey.m3u', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        output = ["#EXTM3U\n"]
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF'):
                output.append(line + "\n")
            elif line.startswith('http') and 'vavoo.to' in line:
                # Kendi Render linkine yönlendiriyoruz
                output.append(f"{base_url}m3u?url={line}\n")
        
        return Response("".join(output), mimetype='audio/x-mpegurl')
    except:
        return "vavoo_Turkey.m3u not found on server", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
