from flask import Flask, request, Response, redirect, jsonify
import requests
import logging
import os
import time
import hashlib
import re
from urllib.parse import quote_plus

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

LOKKE_PING_URL = "https://www.lokke.app/api/app/ping"
LOKKE_TOKEN = "ldCvE092e7gER0rVIajfsXIvRhwlrAzP6_1oEJ4q6HH89QHt24v6NNL_jQJO219hiLOXF2hqEfsUuEWitEIGN4EaHHEHb7Cd7gojc5SQYRFzU3XWo_kMeryAUbcwWnQrnf0-"
RESOLVE_URL = "https://vavoo.to/mediahubmx-resolve.json"
TS_PING2_URL = "https://www.vavoo.tv/api/box/ping2"
TS_VEC = "9frjpxPjxSNilxJPCJ0XGYs6scej3dW/h/VWlnKUiLSG8IP7mfyDU7NirOlld+VtCKGj03XjetfliDMhIev7wcARo+YTU8KPFuVQP9E2DVXzY2BFo1NhE6qEmPfNDnm74eyl/7iFJ0EETm6XbYyz8IKBkAqPN/Spp3PZ2ulKg3QBSDxcVN4R5zRn7OsgLJ2CNTuWkd/h451lDCp+TtTuvnAEhcQckdsydFhTZCK5IiWrrTIC/d4qDXEd+GtOP4hPdoIuCaNzYfX3lLCwFENC6RZoTBYLrcKVVgbqyQZ7DnLqfLqvf3z0FVUWx9H21liGFpByzdnoxyFkue3NzrFtkRL37xkx9ITucepSYKzUVEfyBh+/3mtzKY26VIRkJFkpf8KVcCRNrTRQn47Wuq4gC7sSwT7eHCAydKSACcUMMdpPSvbvfOmIqeBNA83osX8FPFYUMZsjvYNEE3arbFiGsQlggBKgg1V3oN+5ni3Vjc5InHg/xv476LHDFnNdAJx448ph3DoAiJjr2g4ZTNynfSxdzA68qSuJY8UjyzgDjG0RIMv2h7DlQNjkAXv4k1BrPpfOiOqH67yIarNmkPIwrIV+W9TTV/yRyE1LEgOr4DK8uW2AUtHOPA2gn6P5sgFyi68w55MZBPepddfYTQ+E1N6R/hWnMYPt/i0xSUeMPekX47iucfpFBEv9Uh9zdGiEB+0P3LVMP+q+pbBU4o1NkKyY1V8wH1Wilr0a+q87kEnQ1LWYMMBhaP9yFseGSbYwdeLsX9uR1uPaN+u4woO2g8sw9Y5ze5XMgOVpFCZaut02I5k0U4WPyN5adQjG8sAzxsI3KsV04DEVymj224iqg2Lzz53Xz9yEy+7/85ILQpJ6llCyqpHLFyHq/kJxYPhDUF755WaHJEaFRPxUqbparNX+mCE9Xzy7Q/KTgAPiRS41FHXXv+7XSPp4cy9jli0BVnYf13Xsp28OGs/D8Nl3NgEn3/eUcMN80JRdsOrV62fnBVMBNf36+LbISdvsFAFr0xyuPGmlIETcFyxJkrGZnhHAxwzsvZ+Uwf8lffBfZFPRrNv+tgeeLpatVcHLHZGeTgWWml6tIHwWUqv2TVJeMkAEL5PPS4Gtbscau5HM+FEjtGS+KClfX1CNKvgYJl7mLDEf5ZYQv5kHaoQ6RcPaR6vUNn02zpq5/X3EPIgUKF0r/0ctmoT84B2J1BKfCbctdFY9br7JSJ6DvUxyde68jB+Il6qNcQwTFj4cNErk4x719Y42NoAnnQYC2/qfL/gAhJl8TKMvBt3Bno+va8ve8E0z8yEuMLUqe8OXLce6nCa+L5LYK1aBdb60BYbMeWk1qmG6Nk9OnYLhzDyrd9iHDd7X95OM6X5wiMVZRn5ebw4askTTc50xmrg4eic2U1w1JpSEjdH/u/hXrWKSMWAxaj34uQnMuWxPZEXoVxzGyuUbroXRfkhzpqmqqqOcypjsWPdq5BOUGL/Riwjm6yMI0x9kbO8+VoQ6RYfjAbxNriZ1cQ+AW1fqEgnRWXmjt4Z1M0ygUBi8w71bDML1YG6UHeC2cJ2CCCxSrfycKQhpSdI1QIuwd2eyIpd4LgwrMiY3xNWreAF+qobNxvE7ypKTISNrz0iYIhU0aKNlcGwYd0FXIRfKVBzSBe4MRK2pGLDNO6ytoHxvJweZ8h1XG8RWc4aB5gTnB7Tjiqym4b64lRdj1DPHJnzD4aqRixpXhzYzWVDN2kONCR5i2quYbnVFN4sSfLiKeOwKX4JdmzpYixNZXjLkG14seS6KR0Wl8Itp5IMIWFpnNokjRH76RYRZAcx0jP0V5/GfNNTi5QsEU98en0SiXHQGXnROiHpRUDXTl8FmJORjwXc0AjrEMuQ2FDJDmAIlKUSLhjbIiKw3iaqp5TVyXuz0ZMYBhnqhcwqULqtFSuIKpaW8FgF8QJfP2frADf4kKZG1bQ99MrRrb2A="

_lokke_cache = {"sig": None, "time": 0}
_ts_cache = {"sig": None, "time": 0}
_url_cache = {}
CACHE_TIME = 300
SIG_TTL = 300


def get_lokke_sig():
    now = time.time()
    if _lokke_cache["sig"] and (now - _lokke_cache["time"]) < SIG_TTL:
        return _lokke_cache["sig"]
    unique_id = hashlib.md5(str(now).encode()).hexdigest()[:16]
    now_ms = int(now * 1000)
    body = {
        "token": LOKKE_TOKEN,
        "reason": "app-blur",
        "locale": "de",
        "theme": "dark",
        "metadata": {
            "device": {"type": "Handset", "brand": "google", "model": "Nexus", "name": "21081111RG", "uniqueId": unique_id},
            "os": {"name": "android", "version": "7.1.2", "abis": ["arm64-v8a"], "host": "android"},
            "app": {"platform": "android", "version": "1.1.0", "buildId": "97215000", "engine": "hbc85",
                    "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"],
                    "installer": "com.android.vending"},
            "version": {"package": "app.lokke.main", "binary": "1.1.0", "js": "1.1.0"},
            "platform": {"isAndroid": True, "isIOS": False, "isTV": False, "isWeb": False,
                         "isMobile": True, "isWebTV": False, "isElectron": False}
        },
        "appFocusTime": 0, "playerActive": False, "playDuration": 0,
        "devMode": True, "hasAddon": True, "castConnected": False,
        "package": "app.lokke.main", "version": "1.1.0", "process": "app",
        "firstAppStart": now_ms - 86400000, "lastAppStart": now_ms,
        "ipLocation": None, "adblockEnabled": False,
        "proxy": {"supported": ["ss", "openvpn"], "engine": "openvpn", "ssVersion": 1,
                  "enabled": False, "autoServer": True, "id": "fi-hel"},
        "iap": {"supported": True}
    }
    try:
        resp = requests.post(LOKKE_PING_URL, json=body,
                             headers={"user-agent": "okhttp/4.11.0", "content-type": "application/json; charset=utf-8"},
                             timeout=10)
        if resp.status_code == 200:
            sig = resp.json().get("addonSig")
            if sig:
                _lokke_cache["sig"] = sig
                _lokke_cache["time"] = now
                return sig
    except Exception as e:
        app.logger.error(f"Lokke hata: {e}")
    return None


def get_ts_sig():
    now = time.time()
    if _ts_cache["sig"] and (now - _ts_cache["time"]) < SIG_TTL:
        return _ts_cache["sig"]
    try:
        resp = requests.post(TS_PING2_URL, data={"vec": TS_VEC},
                             headers={"content-type": "application/x-www-form-urlencoded"},
                             timeout=10)
        if resp.status_code == 200:
            signed = resp.json().get("response", {}).get("signed")
            if signed:
                _ts_cache["sig"] = signed
                _ts_cache["time"] = now
                return signed
    except Exception as e:
        app.logger.error(f"TS hata: {e}")
    return None


def resolve_url(vavoo_url):
    if vavoo_url in _url_cache:
        t, url = _url_cache[vavoo_url]
        if time.time() - t < CACHE_TIME:
            return url

    # Yontem 1: Lokke + mediahubmx
    sig = get_lokke_sig()
    if sig:
        try:
            resp = requests.post(RESOLVE_URL,
                json={"language": "de", "region": "AT", "url": vavoo_url, "clientVersion": "3.0.2"},
                headers={"user-agent": "MediaHubMX/2", "content-type": "application/json; charset=utf-8",
                         "mediahubmx-signature": sig},
                timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                real_url = None
                if isinstance(data, list) and data:
                    real_url = data[0].get("url")
                elif isinstance(data, dict):
                    real_url = data.get("url") or data.get("data", {}).get("url")
                if real_url:
                    _url_cache[vavoo_url] = (time.time(), real_url)
                    app.logger.info(f"Lokke ile cozuldu")
                    return real_url
        except Exception as e:
            app.logger.error(f"Resolve hata: {e}")

    # Yontem 2: TS ping2 + vavoo_auth
    ts_sig = get_ts_sig()
    if ts_sig:
        m = re.search(r'/play/([^/?#]+)', vavoo_url)
        if m:
            ts_url = f"https://www2.vavoo.to/live2/{m.group(1)}.ts?n=1&b=5&vavoo_auth={quote_plus(ts_sig)}"
            _url_cache[vavoo_url] = (time.time(), ts_url)
            app.logger.info(f"TS fallback ile cozuldu")
            return ts_url

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
    return f"<h1>Vavoo Proxy</h1><p><a href='{base}/turkey.m3u'>turkey.m3u</a></p>"


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
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    base = f"{scheme}://{request.host}"
    lines = ["#EXTM3U\n"]
    for ch in CHANNELS:
        lines.append(f'#EXTINF:-1 tvg-name="{ch["name"]}" group-title="Turkey",{ch["name"]}\n')
        lines.append('#EXTVLCOPT:http-user-agent=MediaHubMX/2\n')
        lines.append('#EXTVLCOPT:http-referrer=https://vavoo.to/\n')
        lines.append(f'{base}/m3u?url=https://vavoo.to/vavoo-iptv/play/{ch["id"]}\n')
    return Response("".join(lines), mimetype="audio/x-mpegurl")


@app.route("/health")
def health():
    sig = get_lokke_sig()
    return jsonify({"status": "ok", "lokke": "ok" if sig else "fail"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
