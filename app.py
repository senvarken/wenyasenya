import os
import json
import subprocess
from flask import Flask, request, Response, jsonify
from functools import lru_cache
import time

app = Flask(__name__)

# ── Yardımcı: yt-dlp çalıştır ────────────────────────────────
def ytdlp(args: list, timeout=30) -> dict | None:
    cmd = ["yt-dlp", "--no-warnings", "--quiet", "--cookies", "/app/cookies.txt"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return None
        return r.stdout.strip()
    except Exception:
        return None

def get_info(url: str, extra: list = []) -> dict | None:
    out = ytdlp(["-j", "--no-playlist"] + extra + [url])
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None

# ── Cache (basit in-memory, 10 dk) ───────────────────────────
_cache = {}
CACHE_TTL = 600  # saniye

def cache_get(key):
    if key in _cache:
        val, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
        del _cache[key]
    return None

def cache_set(key, val):
    _cache[key] = (val, time.time())

# ════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return jsonify({
        "endpoints": {
            "/stream?url=YOUTUBE_URL": "Video/live HLS veya direkt stream URL",
            "/info?url=YOUTUBE_URL": "Video metadata (başlık, thumb, süre)",
            "/m3u?channel=@ASpor": "Kanal → M3U",
            "/m3u?playlist=PLxxx": "Playlist → M3U",
            "/m3u?video=VIDEO_ID": "Tek video → M3U",
            "params": "&type=live|video|all  &limit=30"
        }
    })

# ── /stream — tek video/live stream URL ──────────────────────
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

    # Önce HLS dene (live için)
    info = get_info(url, ["--format", "best[ext=m3u8]/best"])
    if info:
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

    # Normal format
    info = get_info(url, ["--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
    if info:
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

    return jsonify({"error": "Stream URL alınamadı", "url": url}), 404

# ── /info — sadece metadata ──────────────────────────────────
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

    data = get_info(url)
    if not data:
        return jsonify({"error": "Bilgi alınamadı"}), 404

    result = {
        "id": data.get("id"),
        "title": data.get("title"),
        "thumbnail": data.get("thumbnail"),
        "duration": data.get("duration"),
        "uploader": data.get("uploader"),
        "is_live": data.get("is_live", False),
        "view_count": data.get("view_count"),
    }
    cache_set("info:" + url, result)
    return jsonify(result)

# ── /m3u — M3U playlist ──────────────────────────────────────
@app.route("/m3u")
def m3u():
    channel  = request.args.get("channel")
    playlist = request.args.get("playlist")
    video    = request.args.get("video")
    vtype    = request.args.get("type", "all")   # all | live | video
    limit    = min(int(request.args.get("limit", 30)), 100)

    if not channel and not playlist and not video:
        return jsonify({"error": "channel, playlist veya video parametresi gerekli"}), 400

    # URL oluştur
    if video:
        yt_url = f"https://www.youtube.com/watch?v={video}"
        items = fetch_single(yt_url)
    elif playlist:
        yt_url = f"https://www.youtube.com/playlist?list={playlist}"
        items = fetch_list(yt_url, limit)
    else:
        handle = channel if channel.startswith("@") else "@" + channel
        yt_url = f"https://www.youtube.com/{handle}"
        items = fetch_channel(yt_url, limit, vtype)

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

# ── Liste çekme yardımcıları ─────────────────────────────────
def fetch_single(url):
    info = get_info(url, ["--format", "best[ext=m3u8]/best[ext=mp4]/best"])
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
    out = ytdlp([
        "-j", "--flat-playlist",
        "--playlist-end", str(limit),
        yt_url
    ], timeout=60)
    if not out:
        return []

    entries = []
    for line in out.splitlines():
        try:
            e = json.loads(line)
            vid_id = e.get("id") or e.get("url", "").replace("https://www.youtube.com/watch?v=", "")
            if not vid_id:
                continue
            entries.append({
                "id": vid_id,
                "title": e.get("title") or vid_id,
                "thumbnail": e.get("thumbnail") or f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg",
                "duration": e.get("duration"),
                "is_live": e.get("live_status") == "is_live",
            })
        except Exception:
            continue

    # Stream URL'lerini çöz
    return resolve_urls(entries)

def fetch_channel(yt_url, limit, vtype):
    extra = []
    if vtype == "live":
        extra = ["--match-filter", "is_live"]
    elif vtype == "video":
        extra = ["--match-filter", "!is_live"]

    out = ytdlp([
        "-j", "--flat-playlist",
        "--playlist-end", str(limit),
    ] + extra + [yt_url], timeout=60)

    if not out:
        return []

    entries = []
    for line in out.splitlines():
        try:
            e = json.loads(line)
            vid_id = e.get("id") or ""
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
    """Her video için stream URL çöz (sıralı, yavaş ama güvenli)"""
    results = []
    for e in entries:
        url = f"https://www.youtube.com/watch?v={e['id']}"
        cached = cache_get("stream:" + url)
        if cached:
            results.append({**e, "url": cached.get("url")})
            continue

        info = get_info(url, ["--format", "best[ext=m3u8]/best[ext=mp4]/best"])
        if info:
            stream_url = info.get("url") or info.get("manifest_url")
            cache_set("stream:" + url, {"url": stream_url})
            results.append({**e, "url": stream_url,
                           "title": info.get("title") or e["title"],
                           "thumbnail": info.get("thumbnail") or e["thumbnail"],
                           "is_live": info.get("is_live", e["is_live"])})
        else:
            results.append({**e, "url": None})
    return results

# ── /debug — yt-dlp ham çıktısı ─────────────────────────────
@app.route("/debug")
def debug():
    vid = request.args.get("v", "mgeW8Qm8-SY")
    url = f"https://www.youtube.com/watch?v={vid}"
    
    import subprocess
    cmd = ["yt-dlp", "--no-warnings", "-j", "--cookies", "/app/cookies.txt", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return jsonify({
            "returncode": r.returncode,
            "stdout_len": len(r.stdout),
            "stderr": r.stderr[:500] if r.stderr else None,
            "stdout_preview": r.stdout[:200] if r.stdout else None,
        })
    except Exception as e:
        return jsonify({"exception": str(e)})

# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
