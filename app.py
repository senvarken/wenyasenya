from flask import Flask, request, Response, redirect, jsonify
import requests
import json
import logging
import os
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VAVOO_API = "https://vavoo.to/mediahubmx-resolve.json"

cache = {}
CACHE_TIME = 300

def resolve_url(vavoo_url):
    if vavoo_url in cache:
        t, url = cache[vavoo_url]
        if time.time() - t < CACHE_TIME:
            return url

    payload = {
        "language": "tr",
        "region": "TR",
        "url": vavoo_url,
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
            real_url = None
            if isinstance(data, list) and len(data) > 0:
                real_url = data[0].get("url")
            elif isinstance(data, dict):
                real_url = data.get("url") or data.get("streamUrl")
            if real_url:
                cache[vavoo_url] = (time.time(), real_url)
                return real_url
    except Exception as e:
        app.logger.error(f"Resolve hatasi: {e}")
    return None

CHANNELS = [
    {"name": "TRT 1 HD", "id": "1221669131f90e763b2bbf"},
    {"name": "ATV HD", "id": "1332310706d6138ade7950"},
    {"name": "KANAL D HD", "id": "113044193323e36b85a648"},
    {"name": "SHOW TV HD", "id": "8795889605c7795ac9528"},
    {"name": "STAR TV HD", "id": "219297129315c074c03f8e"},
    {"name": "FOX TV HD", "id": "15614953198c1780c4df07"},
    {"name": "TV8 HD", "id": "1702470161fe0c4007a0bb"},
    {"name": "BEYAZ TV HD", "id": "805689873341639546753"},
    {"name": "NTV HD", "id": "2073292907cc209d200015"},
    {"name": "CNN TURK HD", "id": "2056768647bd7eb3f3cf70"},
    {"name": "HABERTURK HD", "id": "11966263871c480a66a299"},
    {"name": "A HABER HD", "id": "535272601f07c2fbd1f2b"},
    {"name": "TRT HABER HD", "id": "6036516388b222edb706e"},
    {"name": "A SPOR HD", "id": "2556711030587eed1d7123"},
    {"name": "TRT SPOR HD", "id": "22629699381f94fcd9dbe6"},
    {"name": "S SPORT HD", "id": "21232735984a3f0b463d66"},
    {"name": "BEIN SPORTS 1 HD", "id": "66217962033a2d3e9c47f"},
    {"name": "BEIN SPORTS 2 HD", "id": "28515391437e928cafd5dd"},
    {"name": "BEIN SPORTS 3 HD", "id": "17005958018c5d23b49ef0"},
    {"name": "TRT COCUK HD", "id": "30291805064bacb8a4036d"},
    {"name": "CARTOON NETWORK", "id": "327818589842dbaee1327c"},
    {"name": "DISNEY CHANNEL HD", "id": "3578544716a4cc42d03dcd"},
    {"name": "TRT MUZIK", "id": "970382162286220f5fa39"},
    {"name": "TEVE2 HD", "id": "1917502631a9b6866e12b6"},
    {"name": "KANAL 7 HD", "id": "109266795988e12fc489b6"},
    {"name": "TRT 2 HD", "id": "38843190334c7e81c1c6fc"},
    {"name": "HALK TV", "id": "1320391955e6c5bb1bedb6"},
    {"name": "24 HABER HD", "id": "3828793616b62b9cc5834c"},
]

@app.route("/")
def index():
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    base = f"{scheme}://{request.host}"
    return f"""<h1>Vavoo Proxy</h1>
    <p><a href='{base}/turkey.m3u'>turkey.m3u</a> - Proxy üzerinden (resolve)</p>
    <p><a href='{base}/direct.m3u'>direct.m3u</a> - Direkt VPN ile</p>"""

@app.route("/m3u")
def m3u_proxy():
    url = request.args.get("url")
    if not url:
        return "URL gerekli", 400
    real_url = resolve_url(url)
    if real_url:
        return redirect(real_url, code=302)
    return jsonify({"error": "cozumlenemedi"}), 502

@app.route("/resolve")
def resolve():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL gerekli"}), 400
    real_url = resolve_url(url)
    if real_url:
        return jsonify({"streamUrl": real_url})
    return jsonify({"error": "cozumlenemedi"}), 502

@app.route("/turkey.m3u")
def turkey_m3u():
    """Proxy üzerinden resolve eder - redirect yapar"""
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    base = f"{scheme}://{request.host}"
    lines = ["#EXTM3U\n"]
    for ch in CHANNELS:
        lines.append(f'#EXTINF:-1 tvg-name="{ch["name"]}" group-title="Turkey",{ch["name"]}\n')
        lines.append('#EXTVLCOPT:http-user-agent=libmpv\n')
        lines.append(f'{base}/m3u?url=https://vavoo.to/vavoo-iptv/play/{ch["id"]}\n')
    return Response("".join(lines), mimetype="audio/x-mpegurl")

@app.route("/direct.m3u")
def direct_m3u():
    """VPN ile direkt açılır - resolve gerekmez"""
    lines = ["#EXTM3U\n"]
    for ch in CHANNELS:
        lines.append(f'#EXTINF:-1 tvg-name="{ch["name"]}" group-title="Turkey",{ch["name"]}\n')
        lines.append('#EXTVLCOPT:http-user-agent=Dalvik/2.1.0 (Linux; U; Android 9; SM-G960F)\n')
        lines.append(f'https://vavoo.to/vavoo-iptv/play/{ch["id"]}\n')
    return Response("".join(lines), mimetype="audio/x-mpegurl")

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
