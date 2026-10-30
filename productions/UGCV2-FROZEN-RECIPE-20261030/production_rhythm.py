import math
import re
from pathlib import Path

from studio import Refused, command, probe, track


def safe_silence_cuts(audio, words, max_pause_s=.48, minimum_silence_s=.8):
    import subprocess
    result = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-i', str(audio),
                             '-af', f'silencedetect=noise=-70dB:d={minimum_silence_s}',
                             '-f', 'null', '-'], capture_output=True, text=True, check=True, timeout=300)
    starts = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', result.stderr)]
    ends = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', result.stderr)]
    cuts = []
    for start, end in zip(starts, ends):
        left = math.ceil((start + max_pause_s / 2) * 25)
        right = math.floor((end - max_pause_s / 2) * 25)
        if right <= left:
            continue
        if any(w['start_s'] < right / 25 and w['end_s'] > left / 25 for w in words):
            continue
        cuts.append((left, right))
    return cuts


def trim_silences(source, audio, words, target, cuts=None):
    meta = probe(source)
    frames = int(track(meta, 'video')['nb_frames'])
    cuts = safe_silence_cuts(audio, words) if cuts is None else cuts
    if not cuts:
        return None
    previous = 0
    ranges = []
    for left, right in cuts:
        if not 0 <= previous <= left < right <= frames:
            raise Refused('RHYTHM_CUT_INVALID')
        if any(w['start_s'] < right / 25 and w['end_s'] > left / 25 for w in words):
            raise Refused('RHYTHM_CUT_INTERSECTS_WORD')
        if left > previous:
            ranges.append((previous, left))
        previous = right
    if previous < frames:
        ranges.append((previous, frames))
    if not ranges:
        raise Refused('RHYTHM_EMPTY_OUTPUT')
    # Check actual samples as well as ASR: missing words in a transcript must
    # not make an audible region eligible for removal.
    import wave
    import numpy as np
    with wave.open(str(audio)) as stream:
        if stream.getframerate() != 48000 or stream.getsampwidth() != 2:
            raise Refused('RHYTHM_NEEDS_PCM16_48K')
        pcm = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').reshape(-1, stream.getnchannels())
    for left, right in cuts:
        samples = pcm[left * 1920:right * 1920].astype(float)
        if not len(samples) or float(np.max(np.abs(samples))) > 32768 * 10 ** (-70 / 20):
            raise Refused('RHYTHM_CUT_NOT_ACTUALLY_SILENT')
    nodes = []
    for i, (left, right) in enumerate(ranges):
        nodes += [f'[0:v]trim=start_frame={left}:end_frame={right},setpts=PTS-STARTPTS[v{i}]',
                  f'[1:a]atrim=start_sample={left * 1920}:end_sample={right * 1920},asetpts=PTS-STARTPTS[a{i}]']
    nodes.append(''.join(f'[v{i}][a{i}]' for i in range(len(ranges))) +
                 f'concat=n={len(ranges)}:v=1:a=1[v][a]')
    command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', source, '-i', audio,
             '-filter_complex', ';'.join(nodes), '-map', '[v]', '-map', '[a]',
             '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', target], timeout=1800)
    return {'removed_frame_intervals': cuts, 'output_frames': sum(b - a for a, b in ranges),
            'audio_speed_changed': False, 'words_intersected': False}
