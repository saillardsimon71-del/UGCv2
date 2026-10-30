import math
import re
import subprocess
import wave
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np

from studio import Refused, command, probe, track


def validate_timeline(data, source_sha, frames, width, height):
    if (data.get('source_sha256'), data.get('frames'), data.get('fps'),
            data.get('width'), data.get('height')) != (source_sha, frames, 25, width, height):
        raise Refused('TIMELINE_SOURCE_MISMATCH')
    position, names = 0, set()
    shots = data.get('shots', [])
    for shot in shots:
        name = shot.get('id', '')
        start, end = shot.get('start_frame'), shot.get('end_frame')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,60}', name) or name in names:
            raise Refused('TIMELINE_SHOT_ID_INVALID')
        names.add(name)
        if type(start) is not int or type(end) is not int or start != position or not start < end <= frames:
            raise Refused('TIMELINE_GAP_OR_OVERLAP')
        mode = shot.get('mode')
        if mode not in ('full', 'pip', 'screen'):
            raise Refused('TIMELINE_LAYOUT_UNQUALIFIED: titles and occlusions need a verified matte')
        if mode == 'pip':
            rectangle = shot.get('rectangle', [])
            if len(rectangle) != 4 or any(type(x) is not int for x in rectangle):
                raise Refused('TIMELINE_PIP_RECTANGLE_REQUIRED')
            x, y, w, h = rectangle
            if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
                raise Refused('TIMELINE_PIP_OUTSIDE_SOURCE')
        position = end
    if position != frames or not shots:
        raise Refused('TIMELINE_INCOMPLETE')
    return shots


def composite_frame(source, foreground, alpha, background, rectangle=None):
    x, y, w, h = rectangle or [0, 0, source.shape[1], source.shape[0]]
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > source.shape[1] or y+h > source.shape[0]:
        raise Refused('COMPOSITE_RECTANGLE_INVALID')
    if foreground.shape != (h, w, 3) or background.shape != foreground.shape or alpha.shape != (h, w):
        raise Refused('COMPOSITE_GEOMETRY_MISMATCH')
    coverage = float(np.mean(alpha > .5))
    if (not np.isfinite(alpha).all() or alpha.min() < 0 or alpha.max() > 1
            or not .02 <= coverage <= .90):
        raise Refused('MATTE_UNRELIABLE: never keep the original background on failure')
    result = source.copy()
    result[y:y+h, x:x+w] = np.rint(foreground * alpha[:, :, None] +
                                  background * (1-alpha[:, :, None])).clip(0, 255).astype(np.uint8)
    return result


def mix_voice(blocks, duration_s, output):
    if not blocks or not math.isfinite(duration_s) or duration_s <= 0:
        raise Refused('VOICE_EMPTY')
    samples = np.zeros(round(duration_s * 48000), dtype='<i2')
    end_previous, selected = 0, []
    for block in blocks:
        start, end = float(block['start_s']), float(block['end_s'])
        if not math.isfinite(start + end) or not 0 <= end_previous <= start < end <= duration_s:
            raise Refused('VOICE_SLOT_OVERLAP')
        path = Path(block['path'])
        if not path.is_file():
            raise Refused('VOICE_FILE_MISSING')
        with wave.open(str(path)) as stream:
            if (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) != (48000, 1, 2):
                raise Refused('VOICE_FORMAT: expected mono PCM16 48kHz')
            pcm = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2')
        slot, size = round((end-start)*48000), len(pcm)
        if not .62*slot <= size <= slot-3840:
            raise Refused('VOICE_SLOT: complete phrase must fill 62 percent and leave 80ms; rewrite text')
        begin = round(start*48000)
        if begin+size > len(samples) or not np.any(pcm):
            raise Refused('VOICE_EMPTY_OR_TRUNCATED')
        # Only fade 8.75ms at waveform edges, as in the reference mix.
        faded = pcm.astype(np.float64)
        fade = min(420, size//5)
        faded[:fade] *= np.linspace(0, 1, fade)
        faded[-fade:] *= np.linspace(1, 0, fade)
        samples[begin:begin+size] = np.rint(faded).astype('<i2')
        selected.append({'id': block['id'], 'start_s': start, 'end_s': end,
                         'duration_s': size/48000, 'end_pause_s': (slot-size)/48000})
        end_previous = end
    with wave.open(str(output), 'wb') as stream:
        stream.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
        stream.writeframes(samples.tobytes())
    return {'audio_speed': 1, 'picture_speed': 1, 'selected': selected,
            'samples': len(samples), 'all_phrases_retained': True}


def extract_shot(source, shot, target):
    start, end = shot['start_frame'], shot['end_frame']
    filters = [f'trim=start_frame={start}:end_frame={end}', 'setpts=PTS-STARTPTS']
    if shot['mode'] == 'pip':
        x, y, w, h = shot['rectangle']
        filters.append(f'crop={w}:{h}:{x}:{y}')
    command(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', source, '-map', '0:v:0',
             '-vf', ','.join(filters), '-an', '-c:v', 'libx264', '-crf', '16',
             '-preset', 'fast', '-pix_fmt', 'yuv420p', target], timeout=1800)
    require_frames(target, end-start)


def require_frames(path, frames):
    video = track(probe(path), 'video')
    if not video or int(video.get('nb_frames', -1)) != frames or Fraction(video['avg_frame_rate']) != 25:
        raise Refused('SHOT_TIMING_CHANGED: no loop, freeze or speed correction')


def cover(image, width, height):
    h, w = image.shape[:2]
    scale = max(width/w, height/h)
    image = cv2.resize(image, (math.ceil(w*scale), math.ceil(h*scale)))
    h, w = image.shape[:2]
    return image[(h-height)//2:(h-height)//2+height, (w-width)//2:(w-width)//2+width]


def replace_background(source, background_path, target, matte_path):
    import mediapipe as mp
    background = cv2.imread(str(background_path))
    if background is None:
        raise Refused('BACKGROUND_PLATE_MISSING')
    video = track(probe(source), 'video')
    width, height, frames = video['width'], video['height'], int(video['nb_frames'])
    background = cover(background, width, height)
    picture = subprocess.Popen(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'rawvideo',
        '-pix_fmt', 'bgr24', '-s', f'{width}x{height}', '-r', '25', '-i', '-', '-an',
        '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p', str(target)],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    matte = subprocess.Popen(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'rawvideo',
        '-pix_fmt', 'gray', '-s', f'{width}x{height}', '-r', '25', '-i', '-',
        '-c:v', 'ffv1', str(matte_path)], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    capture = cv2.VideoCapture(str(source))
    coverage = []
    try:
        with mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1) as segmenter:
            for _ in range(frames):
                ok, frame = capture.read()
                if not ok:
                    raise Refused('MATTE_SOURCE_DECODE_FAILED')
                small = cv2.resize(frame, (480, 270), interpolation=cv2.INTER_AREA)
                raw = segmenter.process(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)).segmentation_mask
                if raw is None or not np.isfinite(raw).all():
                    raise Refused('MATTE_MISSING')
                alpha = cv2.GaussianBlur(np.clip((raw-.22)/.52, 0, 1), (7, 7), 0)
                alpha = cv2.resize(alpha, (width, height))
                result = composite_frame(frame, frame, alpha, background)
                coverage.append(float(np.mean(alpha > .5)))
                picture.stdin.write(result.tobytes())
                matte.stdin.write(np.rint(alpha*255).astype(np.uint8).tobytes())
    except BaseException:
        for process in (picture, matte):
            process.kill()
        raise
    finally:
        capture.release()
        for process in (picture, matte):
            process.stdin.close()
            process.wait(timeout=120)
    if picture.returncode or matte.returncode:
        raise Refused('BACKGROUND_ENCODER_FAILED')
    require_frames(target, frames)
    return {'frames': frames, 'coverage_min': min(coverage), 'coverage_max': max(coverage),
            'model': 'mediapipe_selfie_segmentation_landscape', 'person_pixels_from_video': True,
            'hair_hands_desk_qualified': False}


def assemble_source(source, audio, timeline, clips, target):
    video = track(probe(source), 'video')
    frames = int(video['nb_frames'])
    paths, graph, prior = [], [], '[0:v]'
    for shot in timeline['shots']:
        if shot['mode'] == 'screen':
            continue
        path = clips.get(shot['id'])
        if path is None:
            raise Refused('ASSEMBLY_SHOT_MISSING: ' + shot['id'])
        require_frames(path, shot['end_frame']-shot['start_frame'])
        size = track(probe(path), 'video')
        x, y, w, h = shot.get('rectangle', [0, 0, video['width'], video['height']])
        if (size['width'], size['height']) != (w, h):
            raise Refused('ASSEMBLY_SHOT_GEOMETRY_CHANGED')
        paths.extend(['-i', path])
        index = len(paths)//2
        start, end = shot['start_frame']/25, shot['end_frame']/25
        graph.append(f'[{index}:v]setpts=PTS-STARTPTS+{start}/TB[c{index}]')
        graph.append(f"{prior}[c{index}]overlay={x}:{y}:eof_action=pass:repeatlast=0:"
                     f"enable='gte(t,{start})*lt(t,{end})'[m{index}]")
        prior = f'[m{index}]'
    if not paths:
        raise Refused('ASSEMBLY_NO_REPLACED_PRESENTER')
    command(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', source, *paths, '-i', audio,
        '-filter_complex', ';'.join(graph), '-map', prior, '-map', f'{len(paths)//2+1}:a:0',
        '-frames:v', str(frames), '-r', '25', '-c:v', 'libx264', '-crf', '18',
        '-preset', 'fast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
        '-ar', '48000', '-movflags', '+faststart', target], timeout=1800)
    require_frames(target, frames)
    return {'frames': frames, 'original_timing': True, 'audio_speed': 1,
            'replaced_shots': len(paths)//2}
