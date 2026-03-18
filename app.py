from flask import Flask, request, Response
import requests
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VAVOO_API = "https://vavoo.to/mediahubmx-resolve.json"


@app.route('/')
def index():
    return """
    <h1>Vavoo Proxy Çalışıyor ✅</h1>
    <p>Kullanım: /m3u?url=VAVOO_LINK</p>
    <p>Playlist: /playlist.m3u</p>
    """


@app.route('/m3u')
def m3u_proxy():
    url = request.args.get('url')
    if not url:
        return "URL gerekli", 400

    app.logger.info(f"Çözülüyor: {url}")

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
        # Vavoo resolver API
        resp = requests.post(VAVOO_API, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            return f"API hatası: {resp.status_code}", 500
        data = resp.json()

        # Real HLS URL
        real_url = None
        if isinstance(data, list) and len(data) > 0:
            real_url = data[0].get("url")
        elif isinstance(data, dict):
            real_url = data.get("streamUrl") or data.get("url")
        if not real_url:
            return "URL bulunamadı", 500

        app.logger.info(f"Streaming URL: {real_url}")

        # Stream headers
        stream_headers = {
            "User-Agent": "libmpv",
            "Accept": "*/*",
            "Range": "bytes=0-",
            "Icy-MetaData": "1"
        }

        # Stream proxy
        r = requests.get(real_url, headers=stream_headers, stream=True, timeout=15)

        return Response(
            r.iter_content(chunk_size=1024),
            content_type=r.headers.get('Content-Type', 'application/vnd.apple.mpegurl')
        )

    except Exception as e:
        app.logger.error(str(e))
        return f"Hata: {str(e)}", 500


@app.route('/playlist.m3u')
def playlist():
    BASE_URL = request.host_url.rstrip('/')

    m3u = f"""#EXTM3U

#EXTINF:-1,TRT 1 HD
{BASE_URL}/m3u?url=https://vavoo.to/vavoo-iptv/play/1221669131f90e763b2bbf

#EXTINF:-1,ATV HD
{BASE_URL}/m3u?url=https://vavoo.to/vavoo-iptv/play/1332310706d6138ade7950

#EXTINF:-1,Kanal D HD
{BASE_URL}/m3u?url=https://vavoo.to/vavoo-iptv/play/113044193323e36b85a648

#EXTINF:-1,24 .s
{BASE_URL}/m3u?url=https://vavoo.to/vavoo-iptv/play/17029379329ed4b84db05f
"""
    return Response(m3u, mimetype='audio/x-mpegurl')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
