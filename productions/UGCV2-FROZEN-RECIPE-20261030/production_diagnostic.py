import base64
import json
import os
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from production_input import youtube_id
from production_narration import extract_audio, transcribe, translate_segments, verify_transcript
from production_quality import technical_video
from production_state import PrivateVolume, save_json
from production_workers import (ROOT, RECIPE_PATH, animate, continuation_anchor, frozen_recipe,
                                frozen_text_sha, model_call, synchronize)
from studio import Refused, command, probe, resolve_media, sha256, track

BASE = Path(__file__).resolve().parent
PROFILE_PATH = BASE / 'diagnostic_profile.json'
PROFILE = json.loads(PROFILE_PATH.read_text(encoding='utf-8'))


def pad_utterance(source, target):
    with wave.open(str(source)) as stream:
        if (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) != (48000, 2, 2):
            raise Refused('VOICE_PCM_FORMAT_REQUIRED')
        data = stream.readframes(stream.getnframes())
    frames = len(data) // 4
    leading = 3840
    if frames > 192000 - leading - 5760:
        raise Refused('VOICE_DOES_NOT_FIT_FOUR_SECONDS: no trimming or time stretching allowed')
    with wave.open(str(target), 'wb') as stream:
        stream.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
        stream.writeframes(b'\0' * (leading * 4) + data + b'\0' * ((192000 - leading - frames) * 4))
    return {'duration_s': 4, 'utterance_duration_s': frames / 48000,
            'leading_samples': leading, 'trailing_samples': 192000 - leading - frames,
            'all_utterance_samples_preserved': True, 'speed_changed': False}


def verify_mux_audio(movie, audio):
    with wave.open(str(audio)) as stream:
        expected = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').reshape(-1, 2)
    decoded = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(movie),
                              '-map', '0:a:0', '-ar', '48000', '-ac', '2', '-f', 's16le', '-'],
                             check=True, capture_output=True, timeout=120).stdout
    actual = np.frombuffer(decoded, dtype='<i2').reshape(-1, 2)
    if len(actual) < len(expected):
        raise Refused('DIAGNOSTIC_AUDIO_SHORTENED')
    correlation = float(np.corrcoef(expected.ravel(), actual[:len(expected)].ravel())[0, 1])
    if not np.isfinite(correlation) or correlation < .999:
        raise Refused('DIAGNOSTIC_AUDIO_CHANGED_OR_SHIFTED')
    return {'zero_offset_audio_correlation': correlation, 'complete_pcm_samples': len(expected)}


def fetch_diagnostic(root, output):
    report = json.loads((root / 'report.json').read_text(encoding='utf-8'))
    if report.get('status') != 'DIAGNOSTIC_PRIVATE_UNVALIDATED' or report.get('publish_allowed') is not False:
        raise Refused('NO_PRIVATE_DIAGNOSTIC: successful unvalidated diagnostic receipt required')
    for name, digest in report['diagnostic_files'].items():
        source = resolve_media(root, name)
        if sha256(source) != digest:
            raise Refused('DIAGNOSTIC_CHECKSUM_MISMATCH: ' + name)
    output.mkdir(parents=True, exist_ok=True)
    for name in report['diagnostic_files']:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, destination)
    shutil.copyfile(root / 'report.json', output / 'report.json')


def validate_context(state, url):
    if (os.getenv('GITHUB_ACTIONS') != 'true'
            or os.getenv('GITHUB_REPOSITORY') != 'saillardsimon71-del/UGCv2'):
        raise Refused('GITHUB_EXECUTION_REQUIRED: diagnostic generation runs in the authorized workflow only')
    if state.root.name != PROFILE['mission_run_id'] or youtube_id(url) != PROFILE['youtube_id']:
        raise Refused('FIXED_DIAGNOSTIC_MISSION_REQUIRED: prevent a new run id from resetting GPU limits')
    limits = {'v3': 1, 'ltx': 1, 'tbdub': 1}
    if state.data.get('call_limits', limits) != limits:
        raise Refused('DIAGNOSTIC_CALL_LIMIT_CHANGED')
    state.data['call_limits'] = limits
    state.flush()
    frozen_recipe()
    if frozen_text_sha(ROOT / 'deploy/modal_chatterbox_v3_fr_pilot.py') != PROFILE['voice']['reference_worker_sha256_crlf']:
        raise Refused('REFERENCE_VOICE_WORKER_CHANGED')


def run_diagnostic(state, catalog, url, model_cache, run_stage):
    validate_context(state, url)
    inputs = state.root / 'source-input'
    if not (inputs / 'input-manifest.json').is_file():
        if not PrivateVolume().pull(PROFILE['input_prefix'], inputs):
            raise Refused('DIAGNOSTIC_SOURCE_MISSING')
    manifest = inputs / 'input-manifest.json'
    if sha256(manifest) != PROFILE['input_manifest_sha256']:
        raise Refused('DIAGNOSTIC_SOURCE_MANIFEST_CHANGED')
    files = json.loads(manifest.read_text(encoding='utf-8'))['files']
    for name, digest in files.items():
        if sha256(resolve_media(inputs, name)) != digest:
            raise Refused('DIAGNOSTIC_SOURCE_CHANGED')
    source = json.loads((inputs / 'source.json').read_text(encoding='utf-8'))
    if youtube_id(source['source_url']) != PROFILE['youtube_id']:
        raise Refused('DIAGNOSTIC_SOURCE_URL_CHANGED')
    state.complete('diagnostic_source', files, [manifest, *[inputs / p for p in files]])
    script = state.root / 'new-script.json'
    def adapt():
        result = translate_segments({'language': 'en', 'segments': [{
            'text': source['english_text'], 'start_s': source['selected_local_window_s'][0],
            'end_s': source['selected_local_window_s'][1]}]}, model_cache)[0]
        result['fr_text'] = result['fr_text'][0].upper() + result['fr_text'][1:]
        save_json(script, result)
        return {'french_characters': len(result['fr_text'])}
    run_stage(state, 'diagnostic_adaptation', {'source': sha256(inputs / 'source.json')}, [script], adapt)
    text = json.loads(script.read_text(encoding='utf-8'))['fr_text']
    utterance = state.root / 'new-voice-native.wav'
    voice_receipt = state.root / 'voice-receipt.json'
    def voice():
        import diagnostic_voice as worker
        result = model_call(state, 'new4s/v3/1', worker, worker.speak_once, (text,), 900)
        utterance.write_bytes(base64.b64decode(result['audio_base64'], validate=True))
        save_json(voice_receipt, result['metadata'])
        if sha256(utterance) != result['metadata']['sha256']:
            raise Refused('NEW_VOICE_CHECKSUM_MISMATCH')
        state.data['calls']['new4s/v3/1']['status'] = 'SAVED'
        return result['metadata']
    run_stage(state, 'diagnostic_voice', {'text': text, 'profile': sha256(PROFILE_PATH)},
              [utterance, voice_receipt], voice)
    audio = state.root / 'new-voice-4s.wav'
    speech = state.root / 'new-speech16k.wav'
    pcm = state.root / 'new-voice48k-whole.wav'
    def prepare_audio():
        command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', utterance,
                 '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', pcm])
        report = pad_utterance(pcm, audio)
        extract_audio(audio, speech)
        save_json(state.root / 'audio-preparation.json', report)
        return report
    run_stage(state, 'diagnostic_audio', {'utterance': sha256(utterance)},
              [pcm, audio, speech, state.root / 'audio-preparation.json'], prepare_audio)
    alignment = state.root / 'new-alignment.json'
    def check_narration():
        transcript = transcribe(audio, model_cache, 'fr')
        save_json(alignment, transcript)
        words = [w for seg in transcript['segments'] for w in seg['words']]
        verify_transcript(text, words, 4)
        return {'all_words_recognized': True, 'first_and_last_word_retained': True}
    run_stage(state, 'diagnostic_words', {'audio': sha256(audio), 'text': text},
              [alignment], check_narration)
    previous_raw = catalog / 'FR60-CONTINUITY-8S-20261030/CACHE/trial-1-before-raw.mp4'
    previous = catalog / 'FR60-CONTINUITY-8S-20261030/CACHE/trial-1-before.mp4'
    anchor = state.root / 'continuation-anchor.png'
    run_stage(state, 'diagnostic_anchor', {'native': sha256(previous_raw), 'retained_frames': 100},
              [anchor], lambda: (continuation_anchor(previous_raw, 100, anchor) and {'native_frame': 95}))
    raw, before = animate(state, 'new4s', anchor, attempt=1)
    preflight_receipt = state.root / 'new-face-preflight.json'
    def preflight():
        from deploy import modal_tbdub_fr_worker as worker
        with worker.app.run(name='ugcv2-new4s-face-preflight-cpu', environment_name='main'):
            result = worker.preflight.remote(base64.b64encode(before.read_bytes()).decode(),
                                              base64.b64encode(speech.read_bytes()).decode())
        preview = result.pop('preview_base64')
        (state.root / 'new-face-preview.mp4').write_bytes(base64.b64decode(preview))
        save_json(preflight_receipt, result)
        if result['status'] != 'CPU_FACE_PREFLIGHT_PASSED':
            raise Refused('NEW_TAKE_FACE_PREFLIGHT_FAILED')
        rows = result['face_report']['frame_diagnostics']
        if len(rows) != 100 or any(r['detected_faces'] != 1 or r['landmark_faces'] != 1 for r in rows):
            raise Refused('NEW_TAKE_FACE_DETECTION_INCOMPLETE')
        return {'frames_with_one_face': 100}
    run_stage(state, 'diagnostic_face_preflight', {'before': sha256(before), 'speech': sha256(speech)},
              [preflight_receipt, state.root / 'new-face-preview.mp4'], preflight)
    after = synchronize(state, 'new4s', before, speech, attempt=1)
    output = state.root / 'diagnostic-4s.mp4'
    def mux():
        command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', after, '-i', audio,
                 '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac',
                 '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', output])
        result = technical_video(output, 100)
        result.update(verify_mux_audio(output, audio))
        def video_hash(path):
            return command(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:v:0',
                            '-f', 'streamhash', '-hash', 'SHA256', '-'])
        if video_hash(after) != video_hash(output):
            raise Refused('TBDUB_VIDEO_CHANGED_DURING_MUX')
        result['tbdub_video_preserved'] = True
        return result
    technical = run_stage(state, 'diagnostic_mux', {'after': sha256(after), 'audio': sha256(audio)}, [output], mux)
    if abs(technical['duration_s'] - 4) > .04:
        raise Refused('DIAGNOSTIC_DURATION_CHANGED')
    from production_vision import take_diagnostics
    try:
        measures = take_diagnostics(before, after, previous)
    except Refused as exc:
        measures = {'visual_check': 'REJECTED_OR_UNMEASURABLE', 'diagnostic': str(exc)}
    measures.update(publish_allowed=False, perceptual_validation=PROFILE['perceptual_validation'],
                    narration=state.data['stages']['diagnostic_words']['report'])
    save_json(state.root / 'diagnostic-quality.json', measures)
    reference_voice = state.root / 'reference-voice.wav'
    extract_audio(catalog / 'FR60-PRESENTER-PROOF-20261030/EXPORTS/Clip_A_gros_plan.mp4',
                  reference_voice, rate=48000, channels=2)
    exported = [output, utterance, pcm, audio, speech, script, alignment, voice_receipt, anchor,
                state.root / 'audio-preparation.json', state.root / 'diagnostic-quality.json',
                preflight_receipt, state.root / 'new-face-preview.mp4', raw, before, after,
                raw.parent / 'graph.json', raw.parent / 'ltx.json', raw.parent / 'tbdub.json',
                manifest, reference_voice, state.root / 'state.json', *[inputs / p for p in files]]
    copies = [('recipe.json', RECIPE_PATH), ('diagnostic_profile.json', PROFILE_PATH)]
    for name, original in copies:
        shutil.copyfile(original, state.root / name)
        exported.append(state.root / name)
    diagnostic_files = {p.relative_to(state.root).as_posix(): sha256(p) for p in exported}
    counts = {group: sum('/' + group + '/' in key for key in state.data['calls']) for group in ('v3', 'ltx', 'tbdub')}
    if counts != {'v3': 1, 'ltx': 1, 'tbdub': 1}:
        raise Refused('DIAGNOSTIC_CALL_COUNTS_INVALID')
    return {'status': 'DIAGNOSTIC_PRIVATE_UNVALIDATED', 'publish_allowed': False,
            'new_url_production_ready': False, 'duration_s': 4, 'call_counts': counts,
            'new_gpu_calls': len(state.data['calls']), 'perceptual_validation': PROFILE['perceptual_validation'],
            'diagnostic_sha256': sha256(output), 'diagnostic_files': diagnostic_files,
            'technical_checks': technical, 'github_run_id': os.getenv('GITHUB_RUN_ID'),
            'github_sha': os.getenv('GITHUB_SHA'), 'original_master_regenerated': False}
