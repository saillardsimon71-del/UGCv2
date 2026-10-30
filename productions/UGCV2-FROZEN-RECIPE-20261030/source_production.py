import argparse
import base64
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import cv2

from production_input import download, normalize, youtube_id
from production_narration import extract_audio, transcribe, translate_segments, verify_transcript
from production_quality import technical_video
from production_state import PrivateVolume, RunLock, RunState, fingerprint, safe_id, save_json
from production_workers import french_voice, model_call
from source_media import (assemble_source, extract_shot, mix_voice, replace_background,
                          require_frames, validate_timeline)
from studio import Refused, command, probe, sha256, track

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
# Existing worker adapters prepend ROOT; keep the legacy production module
# ahead of the new root CLI when sibling modules import it.
sys.path.insert(0, str(BASE))
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
RECIPE_SHA = '3d0974159c024366640fc6502982872c8a0d972cc15bc02b62b51db440e0e3f9'
PHASES = ['import', 'analyze', 'adapt', 'voice', 'presenter', 'lips', 'assemble', 'quality', 'export']


def verify_recipe():
    path = BASE / 'source_recipe.json'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != RECIPE_SHA:
        raise Refused('SOURCE_RECIPE_DRIFT')
    recipe = json.loads(path.read_text(encoding='utf-8'))
    for file, expected in recipe['workers'].items():
        digest = hashlib.sha256((ROOT/file).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if digest != expected:
            raise Refused('SOURCE_WORKER_DRIFT: ' + file)
    for asset in ('avatar', 'background'):
        if sha256(ROOT/recipe[asset]['path']) != recipe[asset]['sha256']:
            raise Refused('SOURCE_ASSET_DRIFT: ' + asset)
    return recipe


def require_qualifications(recipe):
    required = ['identity', 'background', 'scene_layout', 'speaker', 'phonetic_lipsync']
    missing = [key for key in required if recipe.get('qualifications', {}).get(key) is not True]
    if missing:
        raise Refused('QUALIFICATION_REQUIRED: ' + ', '.join(missing))


def cached_stage(state, key, inputs, files, operation):
    if state.cached(key, inputs):
        return state.data['stages'][key]['report']
    print('STAGE ' + key, flush=True)
    result = operation()
    state.complete(key, inputs, files, result if isinstance(result, dict) else {})
    return state.data['stages'][key]['report']


def json_stage(state, key, inputs, target, operation):
    def run():
        result = operation()
        save_json(target, result)
        return {'file': target.relative_to(state.root).as_posix()}
    cached_stage(state, key, inputs, [target], run)
    return json.loads(target.read_text(encoding='utf-8'))


def analyze(source):
    from production_vision import analyze_scenes
    result = analyze_scenes(source)
    video = track(probe(source), 'video')
    return {**result, 'source_sha256': sha256(source), 'fps': 25,
            'width': video['width'], 'height': video['height'],
            'production_timeline_qualified': False}


def prepare(state, url, local_source, cache):
    imported = state.root / 'download.mp4'
    if local_source:
        inputs = {'youtube_id': youtube_id(url), 'source_sha256': sha256(local_source)}
        def import_local():
            shutil.copyfile(local_source, imported)
            save_json(state.root/'import.json', {**inputs, 'method': 'explicit_local_authorized_source'})
        cached_stage(state, 'import/download', inputs, [imported, state.root/'import.json'], import_local)
    else:
        cached_stage(state, 'import/download', {'youtube_id': youtube_id(url)},
                     [imported, state.root/'import.json'], lambda: download(url, state.root))
    source = state.root / 'source.mp4'
    cached_stage(state, 'import', {'source': sha256(imported)}, [source], lambda: normalize(imported, source))
    scenes = json_stage(state, 'analyze', {'source': sha256(source)}, state.root/'scenes.json',
                        lambda: analyze(source))
    audio = state.root / 'source16k.wav'
    cached_stage(state, 'adapt/extract', {'source': sha256(source)}, [audio], lambda: extract_audio(source, audio))
    transcript = json_stage(state, 'adapt/transcribe', {'audio': sha256(audio)}, state.root/'transcript.json',
                            lambda: transcribe(audio, cache))
    blocks = json_stage(state, 'adapt', {'transcript': fingerprint(transcript)}, state.root/'french.json',
                        lambda: translate_segments(transcript, cache))
    return source, scenes, blocks


def synthesize(state, blocks, cache, duration):
    selected = []
    for index, block in enumerate(blocks):
        block = {**block, 'id': f'phrase-{index:04d}'}
        response = french_voice(state, [block], batch_id=block['id'])
        folder = state.root/block['id']/'1'
        candidates = response['blocks'][0]['candidates']
        slot = block['end_s']-block['start_s']
        eligible = [c for c in candidates if .62*slot <= c['duration_s'] <= slot-.08]
        if not eligible:
            raise Refused('VOICE_SLOT: adapt French phrase ' + block['id'] + ' before retrying only this stage')
        best = min(eligible, key=lambda c: (abs(slot-.30-c['duration_s']), c['tag'] != 'unhurried'))
        audio = state.root / best['path']
        chosen = folder/'selected48k.wav'
        def convert():
            command(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', audio,
                     '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', chosen])
        cached_stage(state, 'voice/convert/'+block['id'], {'wav': sha256(audio)}, [chosen], convert)
        alignment = json_stage(state, 'voice/words/'+block['id'], {'wav': sha256(chosen)}, folder/'words.json',
                               lambda: transcribe(chosen, cache, 'fr'))
        words = [w for segment in alignment['segments'] for w in segment['words']]
        verify_transcript(block['fr_text'], words, float(probe(chosen)['format']['duration']))
        selected.append({**block, 'path': str(chosen)})
    output = state.root/'narration48k.wav'
    cached_stage(state, 'voice', {'phrases': [{**s, 'sha256': sha256(s['path'])} for s in selected]},
                 [output], lambda: mix_voice(selected, duration, output))
    return output


def replace_presenter(state, source, timeline, recipe):
    from deploy import modal_fr60_faceswap_selected as worker
    portrait = state.root/'avatar.jpg'
    def convert():
        image = cv2.imread(str(ROOT/recipe['avatar']['path']))
        if image is None or not cv2.imwrite(str(portrait), image, [cv2.IMWRITE_JPEG_QUALITY, 98]):
            raise Refused('AVATAR_CONVERSION_FAILED')
    cached_stage(state, 'presenter/avatar', recipe['avatar'], [portrait], convert)
    clips = {}
    for shot in timeline['shots']:
        if shot['mode'] == 'screen':
            continue
        folder = state.root/'shots'/shot['id']
        folder.mkdir(parents=True, exist_ok=True)
        original, identity, background = [folder/name for name in ('original.mp4', 'identity.mp4', 'background.mp4')]
        cached_stage(state, 'presenter/extract/'+shot['id'], {'source': sha256(source), 'shot': shot},
                     [original], lambda: extract_shot(source, shot, original))
        def swap():
            result = model_call(state, 'identity/'+shot['id']+'/1', worker, worker.face_swap_explicit_one,
                                (base64.b64encode(original.read_bytes()).decode(),
                                 base64.b64encode(portrait.read_bytes()).decode()), 1800)
            identity.write_bytes(base64.b64decode(result['video_base64'], validate=True))
            save_json(folder/'identity.json', result['metadata'])
            if sha256(identity) != result['metadata']['sha256']:
                raise Refused('IDENTITY_RESULT_CHECKSUM')
            require_frames(identity, shot['end_frame']-shot['start_frame'])
            state.data['calls']['identity/'+shot['id']+'/1']['status'] = 'SAVED'
        cached_stage(state, 'presenter/identity/'+shot['id'], {'original': sha256(original), 'avatar': sha256(portrait)},
                     [identity, folder/'identity.json'], swap)
        cached_stage(state, 'presenter/background/'+shot['id'],
                     {'identity': sha256(identity), 'background': recipe['background']['sha256']},
                     [background, folder/'alpha.mkv'],
                     lambda: replace_background(identity, ROOT/recipe['background']['path'], background, folder/'alpha.mkv'))
        clips[shot['id']] = background
    return clips


def verified_model_cache(state):
    from deploy import modal_source_lips as worker
    import modal
    def verify_cache():
        with worker.app.run(name='ugcv2-source-model-checksums-cpu', environment_name='main'):
            return worker.verify_cached_models_cpu.remote()
    return json_stage(state, 'lips/cache', {'recipe': RECIPE_SHA}, state.root/'model-cache-receipt.json', verify_cache)


def synchronize(state, clips, timeline, audio):
    from deploy import modal_source_lips as worker
    receipt = verified_model_cache(state)
    results = {}
    for shot in timeline['shots']:
        if shot['mode'] == 'screen':
            continue
        folder = clips[shot['id']].parent
        speech, result_path = folder/'speech16k.wav', folder/'lips.mp4'
        seconds = (shot['end_frame']-shot['start_frame'])/25
        def cut_audio():
            command(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', audio,
                     '-af', f'atrim=start_sample={shot["start_frame"]*1920}:end_sample={shot["end_frame"]*1920},asetpts=PTS-STARTPTS',
                     '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', speech])
        cached_stage(state, 'lips/audio/'+shot['id'], {'audio': sha256(audio), 'shot': shot}, [speech], cut_audio)
        def render():
            result = model_call(state, 'lips/'+shot['id']+'/1', worker, worker.dub_source_shot,
                                (base64.b64encode(clips[shot['id']].read_bytes()).decode(),
                                 base64.b64encode(speech.read_bytes()).decode(), seconds, receipt), 1200)
            result_path.write_bytes(base64.b64decode(result['video_base64'], validate=True))
            if sha256(result_path) != result['metadata']['sha256']:
                raise Refused('LIPS_RESULT_CHECKSUM')
            require_frames(result_path, shot['end_frame']-shot['start_frame'])
            save_json(folder/'lips.json', result['metadata'])
            state.data['calls']['lips/'+shot['id']+'/1']['status'] = 'SAVED'
        cached_stage(state, 'lips/'+shot['id'], {'video': sha256(clips[shot['id']]), 'audio': sha256(speech)},
                     [result_path, folder/'lips.json'], render)
        results[shot['id']] = result_path
    return results


def validate_budget(state, blocks, timeline):
    actors = sum(shot['mode'] != 'screen' for shot in timeline['shots'])
    required = len(blocks)*1200 + actors*(1800+1200)
    if required > state.data['max_gpu_seconds']:
        raise Refused(f'GPU_BUDGET_PREFLIGHT: {required} reserved seconds required before any paid submission')
    return required


def produce(state, source, timeline, blocks, cache, recipe):
    require_qualifications(recipe)
    media = probe(source)
    video = track(media, 'video')
    frames = int(video['nb_frames'])
    validate_timeline(timeline, sha256(source), frames, video['width'], video['height'])
    if any(shot['mode'] != 'screen' and not 1 <= (shot['end_frame']-shot['start_frame'])/25 <= 15
           for shot in timeline['shots']):
        raise Refused('SHOT_LENGTH_UNQUALIFIED: split at a verified original cut; no invented gestures')
    for block in blocks:
        if not 30 <= len(block['fr_text'].strip()) <= 310 or not 4 < block['end_s']-block['start_s'] < 13:
            raise Refused('VOICE_BLOCK_UNSUPPORTED: existing worker requires 30-310 characters, 4-13 seconds')
    validate_budget(state, blocks, timeline)
    verified_model_cache(state)
    audio = synthesize(state, blocks, cache, frames/25)
    presenter = replace_presenter(state, source, timeline, recipe)
    state.complete('presenter', {'clips': {k: sha256(v) for k, v in presenter.items()}}, presenter.values())
    clips = synchronize(state, presenter, timeline, audio)
    state.complete('lips', {'clips': {k: sha256(v) for k, v in clips.items()}}, clips.values())
    candidate = state.root/'candidate.mp4'
    cached_stage(state, 'assemble', {'source': sha256(source), 'audio': sha256(audio), 'timeline': timeline,
                                    'clips': {k: sha256(v) for k, v in clips.items()}}, [candidate],
                 lambda: assemble_source(source, audio, timeline, clips, candidate))
    cached_stage(state, 'quality/technical', {'candidate': sha256(candidate)}, [],
                 lambda: technical_video(candidate, frames))
    # No metric in the repository yet certifies identity or phonetic sync.
    # An editable recipe flag must never turn technical checks into approval.
    raise Refused('PERCEPTUAL_VERIFIER_NOT_IMPLEMENTED: candidate retained, no final export')


def main():
    parser = argparse.ArgumentParser(description='UGCv2 source-performance recipe; zero GPU by default')
    parser.add_argument('--youtube', required=True)
    parser.add_argument('--avatar', choices=['default'], default='default')
    parser.add_argument('--voice', choices=['default'], default='default')
    parser.add_argument('--source', type=Path, help='existing authorized local source, bypass download only')
    parser.add_argument('--timeline', type=Path, help='exact source-bound layout; never inferred from face absence')
    parser.add_argument('--run-id')
    parser.add_argument('--work-root', type=Path, default=ROOT/'data/source-production')
    parser.add_argument('--private-remote', action='store_true')
    parser.add_argument('--cpu-only', action='store_true')
    parser.add_argument('--max-gpu-seconds', type=int, default=0)
    parser.add_argument('--public-report-dir', type=Path)
    args = parser.parse_args()
    if not 0 <= args.max_gpu_seconds <= 86400:
        parser.error('GPU seconds must be between 0 and 86400; full worst-case budget checked before submission')
    identity = youtube_id(args.youtube)
    recipe = verify_recipe()
    dependencies = ['source_production.py', 'source_media.py', 'production_input.py', 'production_narration.py',
                    'production_vision.py', 'production_quality.py', 'production_state.py', 'production_workers.py', 'studio.py']
    code = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in [*(BASE/name for name in dependencies), ROOT/'deploy/modal_source_lips.py']}
    config = {'youtube_id': identity, 'recipe': RECIPE_SHA, 'code': code,
              'source_sha256': sha256(args.source) if args.source else None,
              'timeline_sha256': sha256(args.timeline) if args.timeline else None}
    run_id = safe_id(args.run_id or 'source-'+fingerprint(config)[:16])
    root = args.work_root.resolve()/run_id
    volume = PrivateVolume() if args.private_remote else None
    if volume and not (root/'state.json').exists():
        volume.pull('source-runs/'+run_id, root)
    root.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'ugcv2.source-report/v1', 'run_id': run_id, 'recipe_sha256': RECIPE_SHA,
              'autonomous': False, 'new_gpu_calls': 0, 'status': 'BLOCKED', 'phases': {k: 'PENDING' for k in PHASES}}
    state = None
    with RunLock(root/'production.lock'):
        try:
            state = RunState(root, config, args.max_gpu_seconds,
                             (lambda p: volume.push('source-runs/'+run_id, p)) if volume else None)
            calls_before = len(state.data['calls'])
            source, scenes, blocks = prepare(state, args.youtube, args.source, args.work_root/'cpu-model-cache')
            if args.cpu_only:
                report.update(status='CPU_ANALYSIS_COMPLETE', limitations=['French translation is not visual editorial adaptation',
                              'Scene candidates are not a qualified timeline', 'No new voice, identity or lips generated'])
            else:
                require_qualifications(recipe)
                if not args.timeline:
                    raise Refused('SCENE_TIMELINE_UNQUALIFIED: exact PiP and title handling missing')
                timeline = json.loads(args.timeline.read_text(encoding='utf-8'))
                produce(state, source, timeline, blocks, args.work_root/'cpu-model-cache', recipe)
        except Exception as exc:
            message = str(exc)
            code = message.split(':', 1)[0]
            if not re.fullmatch('[A-Z][A-Z0-9_]{2,79}', code):
                code = 'PIPELINE_ERROR'
            report.update(status='BLOCKED', blocker_code=code)
            save_json(root/'error.json', {'code': code, 'detail': message, 'exception': type(exc).__name__})
        finally:
            if state:
                report['new_gpu_calls'] = max(0, len(state.data['calls'])-locals().get('calls_before', 0))
                report['reserved_gpu_seconds'] = sum(c['reserved_seconds'] for c in state.data['calls'].values())
                for phase in PHASES:
                    if phase in state.data['stages']:
                        report['phases'][phase] = 'COMPLETED'
                if volume:
                    save_json(root/'report.json', report)
                    volume.push('source-runs/'+run_id, root)
            save_json(root/'report.json', report)
            if args.public_report_dir:
                save_json(args.public_report_dir/'source-report.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'CPU_ANALYSIS_COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
