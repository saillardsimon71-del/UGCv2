from studio import Refused, command, probe, track


def require_qualified_generation():
    # A face box and a stable background do not measure phonetic lip sync or
    # whether the performance still looks human. Never auto-approve on these.
    raise Refused('LIPSYNC_VALIDATOR_UNQUALIFIED: no calibrated perceptual verifier '
                  'against approved Work clips and rejected 20s/60s renders. '
                  'New takes may be diagnostic only; approved bytes remain usable.')


def technical_video(path, frames=None):
    media = probe(path)
    video, audio = track(media, 'video'), track(media, 'audio')
    if not video or not audio:
        raise Refused('QUALITY_TRACK_MISSING')
    if frames is not None and int(video.get('nb_frames', -1)) != frames:
        raise Refused('QUALITY_FRAME_COUNT_CHANGED')
    command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', path, '-f', 'null', '-'], timeout=1800)
    return {'full_decode': True, 'frames': int(video.get('nb_frames', -1)),
            'duration_s': float(media['format']['duration']),
            'natural_human_performance_certified': False}
