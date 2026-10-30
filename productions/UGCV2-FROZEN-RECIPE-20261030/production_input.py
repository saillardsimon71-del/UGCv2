import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from studio import Refused, command, probe, sha256, track
from production_state import save_json


def youtube_id(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port:
            raise ValueError()
        host = (parsed.hostname or '').lower()
        if host == 'youtu.be':
            value = parsed.path.strip('/')
        elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
            if parsed.path == '/watch':
                value = parse_qs(parsed.query).get('v', [''])[0]
            elif parsed.path.startswith(('/shorts/', '/embed/')):
                value = parsed.path.split('/')[2]
            else:
                raise ValueError()
        else:
            raise ValueError()
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', value):
            raise ValueError()
        return value
    except (ValueError, IndexError):
        raise Refused('INVALID_YOUTUBE_URL: provide one https YouTube video URL') from None


def download(url, root, max_seconds=900, max_bytes=1_000_000_000):
    identity = youtube_id(url)
    root = Path(root)
    target = root / 'download.mp4'
    canonical = 'https://www.youtube.com/watch?v=' + identity
    base = [sys.executable, '-m', 'yt_dlp', '--no-playlist', '--no-warnings',
            '--socket-timeout', '30', '--retries', '2', '--extractor-retries', '2']
    try:
        metadata = json.loads(command([*base, '--skip-download', '--dump-single-json', canonical], timeout=150))
        duration = metadata.get('duration')
        if not isinstance(duration, (int, float)) or not 0 < duration <= max_seconds or metadata.get('is_live'):
            raise Refused('SOURCE_LIMIT: unavailable duration, live video or duration budget exceeded')
        command([*base, '--no-overwrites', '--max-filesize', str(max_bytes),
                 '-f', 'bv*[height<=1080]+ba/b[height<=1080]', '--merge-output-format', 'mp4',
                 '--remux-video', 'mp4', '-o', target, canonical], timeout=1200)
    except Refused as exc:
        target.unlink(missing_ok=True)
        raise Refused('YOUTUBE_DOWNLOAD_FAILED: video unavailable, restricted or download failed. ' + str(exc)[-1200:]) from exc
    if not target.is_file() or target.stat().st_size > max_bytes:
        raise Refused('SOURCE_LIMIT: no complete download within size budget')
    save_json(root / 'import.json', {'youtube_id': identity, 'source_url': canonical,
                                   'sha256': sha256(target), 'bytes': target.stat().st_size,
                                   'duration_s': duration})
    return target


def normalize(source, target):
    info = probe(source)
    v, a = track(info, 'video'), track(info, 'audio')
    if not v or not a:
        raise Refused('SOURCE_TRACKS_MISSING: narration and picture required')
    if v['width'] < v['height']:
        raise Refused('SOURCE_LAYOUT_UNQUALIFIED: portrait input not covered by approved landscape recipe')
    command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-y', '-i', source,
             '-map', '0:v:0', '-map', '0:a:0', '-vf',
             'fps=25,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1',
             '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', target], timeout=1800)
    return {'original': info, 'normalized': probe(target), 'original_sha256': sha256(source)}
