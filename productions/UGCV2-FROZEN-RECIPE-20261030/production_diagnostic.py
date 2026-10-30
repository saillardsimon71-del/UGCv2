import base64
import json
import os
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from production_input import youtube_id
from production_narration import extract_audio, tokens, transcribe, translate_segments, verify_transcript
from production_quality import technical_video
from production_state import PrivateVolume, fingerprint, save_json
from production_workers import (ROOT, RECIPE_PATH, animate, continuation_anchor, frozen_recipe,
                                frozen_text_sha, model_call, synchronize)
from studio import Refused, check_word_boundaries, command, probe, resolve_media, sha256, track

BASE = Path(__file__).resolve().parent
PROFILE_PATH = BASE / 'diagnostic_profile.json'
PROFILE = json.loads(PROFILE_PATH.read_text(encoding='utf-8'))
RESUME_LOCK_PATH = BASE / 'human_voice_approval_lock.json'
RESUME_LOCK = json.loads(RESUME_LOCK_PATH.read_text(encoding='utf-8'))


def load_human_voice_approval(root, volume):
    if root.name != RESUME_LOCK['run_id']:
        return None
    folder = root / 'human-approval'
    file = folder / 'voice-human-approval.json'
    if not file.is_file():
        if volume is None or not volume.pull(RESUME_LOCK['approval_prefix'], folder):
            raise Refused('EXPLICIT_VOICE_APPROVAL_MISSING')
    if sha256(file) != RESUME_LOCK['approval_sha256']:
        raise Refused('EXPLICIT_VOICE_APPROVAL_CHANGED')
    return json.loads(file.read_text(encoding='utf-8'))


def check_human_approved_narration(root, text, approval):
    if (not isinstance(approval, dict) or approval.get('schema') != 'ugcv2.human-voice-approval/v1'
            or approval.get('run_id') != root.name or root.name != PROFILE['mission_run_id']
            or approval.get('authority') != 'explicit_user_validation_in_current_chat'
            or approval.get('scope') != 'exact_voice_only_not_video_or_general_asr'
            or approval.get('human_confirmed_whole_utterance') is not True
            or approval.get('voice_regeneration_allowed') is not False
            or approval.get('expected_text') != text):
        raise Refused('EXACT_HUMAN_VOICE_APPROVAL_REQUIRED')
    for name, field in [('new-voice-native.wav', 'native_wav_sha256'),
                        ('new-voice48k-whole.wav', 'whole_pcm_sha256'),
                        ('new-voice-4s.wav', 'padded_wav_sha256'),
                        ('new-speech16k.wav', 'speech16k_sha256'),
                        ('new-alignment.json', 'asr_sha256')]:
        if sha256(root / name) != approval.get(field):
            raise Refused('APPROVED_VOICE_FILE_CHANGED: ' + name)
    transcript = json.loads((root / 'new-alignment.json').read_text(encoding='utf-8'))
    if transcript != approval.get('asr_result'):
        raise Refused('APPROVED_ASR_RECORD_CHANGED')
    samples = []
    for name in ('new-voice48k-whole.wav', 'new-voice-4s.wav'):
        with wave.open(str(root / name)) as stream:
            if (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) != (48000, 2, 2):
                raise Refused('VOICE_PCM_FORMAT_REQUIRED')
            samples.append(np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').reshape(-1, 2))
    whole, padded = samples
    first, last = 3840, 3840 + len(whole)
    if len(padded) != 192000 or not 0 < len(whole) <= 182400:
        raise Refused('VOICE_DURATION_CHANGED')
    if first < 960 or len(padded) - last < 1920 or np.any(padded[:first]) or np.any(padded[last:]):
        raise Refused('VOICE_EDGE_GUARD_MISSING')
    if not np.array_equal(padded[first:last], whole):
        raise Refused('VOICE_SAMPLES_CHANGED')
    words = [w for segment in transcript['segments'] for w in segment['words']]
    check_word_boundaries(words, 0, 100, 25)
    asr_error = None
    try:
        verify_transcript(text, words, 4)
    except Refused as exc:
        asr_error = str(exc)
    return {'human_approved_exact_voice': True, 'expected_text': text,
            'native_wav_sha256': approval['native_wav_sha256'],
            'all_words_recognized': tokens(text) == tokens(' '.join(w['text'] for w in words)),
            'asr_check_error': asr_error, 'asr_contradiction': transcript,
            'first_and_last_word_retained': True, 'phrase_validation': 'explicit_whole_wav_human_approval',
            'leading_guard_samples': first, 'trailing_guard_samples': len(padded) - last,
            'all_utterance_samples_preserved': True, 'voice_speed_changed': False}


def authorize_voice_resume(root, config, max_gpu_seconds, approval):
    base = RESUME_LOCK['base_configuration']
    expected_fields = {key: value for key, value in base.items() if key != 'code'}
    actual_fields = {key: value for key, value in config.items()
                     if key not in ('code', 'human_voice_approval_lock_sha256')}
    if (root.name != RESUME_LOCK['run_id'] or max_gpu_seconds != RESUME_LOCK['max_gpu_seconds']
            or actual_fields != expected_fields
            or config.get('human_voice_approval_lock_sha256') != sha256(RESUME_LOCK_PATH)
            or set(config['code']) != set(base['code'])):
        raise Refused('UNAUTHORIZED_RESUME_CONFIGURATION_CHANGE')
    for name, digest in config['code'].items():
        if name not in RESUME_LOCK['allowed_changed_code'] and digest != base['code'][name]:
            raise Refused('UNAUTHORIZED_RESUME_CODE_CHANGE: ' + name)
    text = json.loads((root / 'new-script.json').read_text(encoding='utf-8'))['fr_text']
    check_human_approved_narration(root, text, approval)
    state_path = root / 'state.json'
    data = json.loads(state_path.read_text(encoding='utf-8'))
    target = fingerprint({'config': config, 'max_gpu_seconds': max_gpu_seconds})
    if data['configuration'] == target:
        return
    if (data['configuration'] != approval.get('original_configuration')
            or sha256(state_path) != approval.get('original_state_sha256')
            or data['max_gpu_seconds'] != max_gpu_seconds
            or set(data['calls']) != {'new4s/v3/1'}
            or data['calls']['new4s/v3/1']['status'] != 'SAVED'):
        raise Refused('UNAUTHORIZED_RESUME_STATE_CHANGED')
    for stage in data['stages'].values():
        for name, digest in stage['files'].items():
            if sha256(resolve_media(root, name)) != digest:
                raise Refused('RESUME_INTERMEDIATE_CHANGED: ' + name)
    shutil.copyfile(state_path, root / 'state-before-human-approval.json')
    if (root / 'report.json').exists():
        shutil.copyfile(root / 'report.json', root / 'report-before-human-approval.json')
    data['configuration_history'] = [{'from': data['configuration'], 'to': target,
                                     'reason': 'explicit_exact_wav_human_approval',
                                     'approval_sha256': RESUME_LOCK['approval_sha256']}]
    data['configuration'] = target
    save_json(state_path, data)


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


def run_diagnostic(state, catalog, url, model_cache, run_stage, human_approval=None):
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
    voice_inputs = {'text': text, 'profile': sha256(PROFILE_PATH)}
    if human_approval is not None and not state.cached('diagnostic_voice', voice_inputs):
        raise Refused('APPROVED_VOICE_CACHE_REQUIRED_NO_CHATTERBOX_REGENERATION')
    run_stage(state, 'diagnostic_voice', voice_inputs,
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
        if human_approval is not None:
            return check_human_approved_narration(state.root, text, human_approval)
        transcript = transcribe(audio, model_cache, 'fr')
        save_json(alignment, transcript)
        words = [w for seg in transcript['segments'] for w in seg['words']]
        verify_transcript(text, words, 4)
        return {'all_words_recognized': True, 'first_and_last_word_retained': True}
    word_inputs = {'audio': sha256(audio), 'text': text}
    word_outputs = [alignment]
    if human_approval is not None:
        word_inputs['human_approval_sha256'] = RESUME_LOCK['approval_sha256']
        def checked_with_receipt():
            result = check_narration()
            save_json(state.root / 'voice-validation.json', result)
            return result
        word_outputs.append(state.root / 'voice-validation.json')
        run_stage(state, 'diagnostic_words', word_inputs, word_outputs, checked_with_receipt)
    else:
        run_stage(state, 'diagnostic_words', word_inputs, word_outputs, check_narration)
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
    if human_approval is not None:
        exported += [state.root / 'human-approval/voice-human-approval.json',
                     state.root / 'voice-validation.json', state.root / 'state-before-human-approval.json']
        if (state.root / 'report-before-human-approval.json').exists():
            exported.append(state.root / 'report-before-human-approval.json')
        copies.append(('human_voice_approval_lock.json', RESUME_LOCK_PATH))
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
            'github_sha': os.getenv('GITHUB_SHA'), 'original_master_regenerated': False,
            'human_voice_approved': human_approval is not None, 'voice_regenerated': False}
