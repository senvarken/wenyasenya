import os
import json
import asyncio
import subprocess
from flask import Flask, request, Response, jsonify
import time

app = Flask(__name__)

_cache = {}
CACHE_TTL = 600

def cache_get(key):
    if key in _cache:
        val, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
        del _cache[key]
    return None

def cache_set(key, val):
    _cache[key] = (val, time.time())

COOKIES = "/app/cookies.txt"

def ytdlp(args, timeout=60):
    cmd = ["yt-dlp", "--no-warnings", "--quiet", "--cookies", COOKIES] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return None, r.stderr
        return r.stdout.strip(), None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)

def get_info(url, extra=[]):
    out, err = ytdlp(["-j", "--no-playlist"] + extra + [url])
    if not out:
        return None, err
    try:
        return json.loads(out), None
    except Exception as e:
        return None, str(e)

@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "endpoints": {
            "/stream?v=VIDEO_ID": "Stream URL",
            "/info?v=VIDEO_ID": "Video metadata",
            "/m3u?channel=@ASpor": "Kanal M3U",
            "/m3u?playlist=PLxxx": "Playlist M3U",
            "/m3u?video=VIDEO_ID": "Tek video M3U",
            "/debug?v=VIDEO_ID": "Ham yt-dlp çıktısı",
        }
    })

@app.route("/debug")
def debug():
    vid = request.args.get("v", "mgeW8Qm8-SY")
    url = f"https://www.youtube.com/watch?v={vid}"
    cmd = ["yt-dlp", "--no-warnings", "--cookies", COOKIES, "-j", "--no-playlist", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        data = None
        if r.stdout:
            try:
                d = json.loads(r.stdout)
                data = {
                    "title": d.get("title"),
                    "is_live": d.get("is_live"),
                    "url_present": bool(d.get("url") or d.get("manifest_url")),
                    "hls": d.get("manifest_url") or d.get("url", "")[:80],
                }
            except Exception:
                data = r.stdout[:300]
        return jsonify({
            "returncode": r.returncode,
            "stderr": r.stderr[:500] if r.stderr else None,
            "data": data,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "yt-dlp timeout (60s)"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/stream")
def stream():
    url = request.args.get("url")
    vid = request.args.get("v") or request.args.get("video")
    if vid and not url:
        url = f"https://www.youtube.com/watch?v={vid}"
    if not url:
        return jsonify({"error": "url veya v parametresi gerekli"}), 400

    cached = cache_get("stream:" + url)
    if cached:
        return jsonify(cached)

    info, err = get_info(url, ["--format", "best[ext=m3u8]/best[ext=mp4]/best"])
    if not info:
        return jsonify({"error": "Stream URL alınamadı", "detail": err}), 404

    result = {
        "id": info.get("id"),
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "is_live": info.get("is_live", False),
        "url": info.get("url") or info.get("manifest_url"),
    }
    if result["url"]:
        cache_set("stream:" + url, result)
    return jsonify(result)

@app.route("/info")
def info():
    url = request.args.get("url")
    vid = request.args.get("v") or request.args.get("video")
    if vid and not url:
        url = f"https://www.youtube.com/watch?v={vid}"
    if not url:
        return jsonify({"error": "url parametresi gerekli"}), 400

    cached = cache_get("info:" + url)
    if cached:
        return jsonify(cached)

    data, err = get_info(url)
    if not data:
        return jsonify({"error": "Bilgi alınamadı", "detail": err}), 404

    result = {
        "id": data.get("id"),
        "title": data.get("title"),
        "thumbnail": data.get("thumbnail"),
        "duration": data.get("duration"),
        "uploader": data.get("uploader"),
        "is_live": data.get("is_live", False),
    }
    cache_set("info:" + url, result)
    return jsonify(result)

@app.route("/m3u")
def m3u():
    channel  = request.args.get("channel")
    playlist = request.args.get("playlist")
    video    = request.args.get("video")
    vtype    = request.args.get("type", "all")
    limit    = min(int(request.args.get("limit", 30)), 100)

    if not channel and not playlist and not video:
        return jsonify({"error": "channel, playlist veya video gerekli"}), 400

    if video:
        items = fetch_single(f"https://www.youtube.com/watch?v={video}")
    elif playlist:
        items = fetch_list(f"https://www.youtube.com/playlist?list={playlist}", limit)
    else:
        handle = channel if channel.startswith("@") else "@" + channel
        items = fetch_channel(f"https://www.youtube.com/{handle}", limit, vtype)

    if not items:
        return Response("#EXTM3U\n# Sonuç bulunamadı", mimetype="text/plain")

    lines = ["#EXTM3U"]
    for item in items:
        if not item.get("url"):
            continue
        dur   = -1 if item.get("is_live") else int(item.get("duration") or -1)
        group = "YouTube Live" if item.get("is_live") else "YouTube"
        title = (item.get("title") or item.get("id") or "Video").replace(",", " ")
        thumb = item.get("thumbnail") or ""
        lines.append(f'#EXTINF:{dur} tvg-logo="{thumb}" group-title="{group}",{title}')
        lines.append(item["url"])

    return Response("\n".join(lines), mimetype="application/x-mpegURL",
                    headers={"Content-Disposition": 'attachment; filename="youtube.m3u"',
                             "Access-Control-Allow-Origin": "*"})

def fetch_single(url):
    info, _ = get_info(url, ["--format", "best[ext=m3u8]/best[ext=mp4]/best"])
    if not info:
        return []
    return [{
        "id": info.get("id"),
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "is_live": info.get("is_live", False),
        "url": info.get("url") or info.get("manifest_url"),
    }]

def fetch_list(yt_url, limit):
    out, _ = ytdlp(["-j", "--flat-playlist", "--playlist-end", str(limit), yt_url], timeout=90)
    if not out:
        return []
    entries = []
    for line in out.splitlines():
        try:
            e = json.loads(line)
            vid_id = e.get("id", "")
            if not vid_id:
                continue
            entries.append({
                "id": vid_id,
                "title": e.get("title") or vid_id,
                "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
                "duration": e.get("duration"),
                "is_live": e.get("live_status") == "is_live",
            })
        except Exception:
            continue
    return resolve_urls(entries)

def fetch_channel(yt_url, limit, vtype):
    extra = []
    if vtype == "live":
        extra = ["--match-filter", "is_live"]
    elif vtype == "video":
        extra = ["--match-filter", "!is_live"]
    out, _ = ytdlp(["-j", "--flat-playlist", "--playlist-end", str(limit)] + extra + [yt_url], timeout=90)
    if not out:
        return []
    entries = []
    for line in out.splitlines():
        try:
            e = json.loads(line)
            vid_id = e.get("id", "")
            if not vid_id:
                continue
            entries.append({
                "id": vid_id,
                "title": e.get("title") or vid_id,
                "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
                "duration": e.get("duration"),
                "is_live": e.get("live_status") == "is_live",
            })
        except Exception:
            continue
    return resolve_urls(entries)

def resolve_urls(entries):
    results = []
    for e in entries:
        url = f"https://www.youtube.com/watch?v={e['id']}"
        cached = cache_get("stream:" + url)
        if cached:
            results.append({**e, "url": cached.get("url")})
            continue
        info, _ = get_info(url, ["--format", "best[ext=m3u8]/best[ext=mp4]/best"])
        if info:
            stream_url = info.get("url") or info.get("manifest_url")
            cache_set("stream:" + url, {"url": stream_url})
            results.append({**e, "url": stream_url,
                           "title": info.get("title") or e["title"],
                           "is_live": info.get("is_live", e["is_live"])})
        else:
            results.append({**e, "url": None})
    return results

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
