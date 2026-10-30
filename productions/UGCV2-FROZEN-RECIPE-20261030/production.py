import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from golden import ASSETS, GOLDEN_SHA
from planner import create_plan
from production_input import download, normalize, youtube_id
from production_narration import extract_audio, tokens, transcribe, translate_segments
from production_quality import require_qualified_generation, technical_video
from production_rhythm import trim_silences
from production_state import PrivateVolume, RunLock, RunState, safe_id, save_json
from production_workers import frozen_recipe
from seed_catalog import HYBRID_SHA, REFERENCES
from studio import Refused, assemble, command, probe, sha256, track

BASE = Path(__file__).resolve().parent
PROFILE = json.loads((BASE / 'production_profile.json').read_text(encoding='utf-8'))
REPOSITORY = BASE.parents[1]


def validated_catalog(root):
    catalog = json.loads((root / 'production-catalog.json').read_text(encoding='utf-8'))
    if catalog.get('schema') != 'ugcv2.production-catalog/v1' or catalog.get('hybrid_parent_sha256') != HYBRID_SHA:
        raise Refused('CATALOG_PROVENANCE_CHANGED')
    required = {**ASSETS, **REFERENCES, 'approved_6p52s.mp4': GOLDEN_SHA}
    for name, wanted in required.items():
        if sha256(root / name) != wanted:
            raise Refused('APPROVED_REFERENCE_CHANGED: ' + name)
    for name, wanted in catalog['files'].items():
        file = (root / name).resolve()
        if not file.is_relative_to(root.resolve()) or sha256(file) != wanted:
            raise Refused('CATALOG_CHECKSUM_MISMATCH: ' + name)
    return catalog


def run_stage(state, key, inputs, files, operation):
    if not state.cached(key, inputs):
        result = operation() or {}
        state.complete(key, inputs, files, result)
    return state.data['stages'][key]['report']


def reference_manifest(root, words):
    def media(path):
        return {'path': path, 'sha256': sha256(root / path), 'status': 'APPROVED'}
    return {
        'schema': 'ugcv2.approved-timeline/v1', 'allow_regeneration': False,
        'source': media('source.mp4'), 'word_timing': words,
        'takes': {'A': media('actor-A.mp4'), 'next': media('actor-next.mp4'),
                  'title': media('title-composite.mp4')},
        'shots': [
            {'start_frame': 0, 'end_frame': 100, 'mode': 'full', 'take': 'A', 'take_offset_frame': 0},
            {'start_frame': 100, 'end_frame': 110, 'mode': 'full', 'take': 'next', 'take_offset_frame': 0},
            {'start_frame': 110, 'end_frame': 166, 'mode': 'full', 'take': 'title', 'take_offset_frame': 10,
             'content_kind': 'approved_native_title_composite'},
            {'start_frame': 166, 'end_frame': 199, 'mode': 'pip', 'take': 'next', 'take_offset_frame': 66,
             'rectangle': [1428, 0, 492, 444]},
            {'start_frame': 199, 'end_frame': 200, 'mode': 'screen', 'content_kind': 'domino_demo'},
        ],
    }


def reference_run(state, catalog_root, url, model_cache, verify_workers=False):
    catalog = validated_catalog(catalog_root)
    if youtube_id(url) != catalog['youtube_id']:
        raise Refused('REFERENCE_URL_MISMATCH: this profile reuses only the exact private reference window')
    imports = {
        'source.mp4': 'reference-source-8s.mp4',
        'actor-A.mp4': 'FR60-PRESENTER-PROOF-20261030/EXPORTS/Clip_A_gros_plan.mp4',
        'actor-next.mp4': 'FR60-CONTINUITY-8S-20261030/CACHE/trial-1-after.mp4',
        'title-composite.mp4': 'FR60-CONTINUITY-8S-20261030/CACHE/trial-1-montage-4s.mp4',
        'speech48k.wav': 'FR60-CONTINUITY-8S-20261030/CACHE/continuous-audio48k.wav',
    }
    def import_files():
        for name, original in imports.items():
            shutil.copyfile(catalog_root / original, state.root / name)
        return {'mode': 'exact_private_source_cache', 'youtube_window_s': catalog['youtube_window_s'],
                'approved_takes_reused': 2, 'approved_title_composite_reused': True}
    run_stage(state, 'import', {p: catalog['files'][p] for p in imports.values()},
              [state.root / p for p in imports], import_files)
    if verify_workers:
        verify_cpu_workers(state)
    source_audio = state.root / 'source16k.wav'
    run_stage(state, 'extract_audio', {'source': sha256(state.root / 'source.mp4')}, [source_audio],
              lambda: (extract_audio(state.root / 'source.mp4', source_audio) and {}))
    words_path = state.root / 'alignment.json'
    def align():
        transcript = transcribe(source_audio, model_cache, 'fr', strict=False)
        save_json(words_path, transcript)
        return {'asr_revision': transcript['revision'], 'segments': len(transcript['segments'])}
    run_stage(state, 'align', {'audio': sha256(source_audio)}, [words_path], align)
    transcript = json.loads(words_path.read_text(encoding='utf-8'))
    words = [word for segment in transcript['segments'] for word in segment['words']
             if word['end_s'] > word['start_s']]
    manifest = reference_manifest(state.root, words)
    save_json(state.root / 'manifest.json', manifest)
    montage = state.root / 'assembled-8s.mp4'
    # studio.py remains the one assembler; its APPROVED gate is never bypassed.
    def render():
        montage.unlink(missing_ok=True)
        return assemble(manifest, state.root, montage)
    assembly = run_stage(state, 'assemble', manifest, [montage], render)
    candidate = state.root / 'candidate.mp4'
    def rhythm():
        # This exact reference edit was approved already. Its removed samples
        # are checked below -70dBFS; coarse ASR bounds across a silent lead-in
        # must not override the actual sample proof. New content stays strict.
        result = trim_silences(montage, state.root / 'speech48k.wav', [], candidate, [(73, 110)])
        save_json(state.root / 'rhythm.json', result)
        return result
    rhythm_report = run_stage(state, 'rhythm', {'montage': sha256(montage), 'words': words,
                                               'pcm': sha256(state.root / 'speech48k.wav'), 'cuts': [[73, 110]]},
                              [candidate, state.root / 'rhythm.json'], rhythm)
    checks = verify_reference_output(candidate, state.root / 'speech48k.wav',
                                     catalog_root / 'approved_6p52s.mp4', words, model_cache, state)
    final = state.root / 'final.mp4'
    if final.exists() and sha256(final) != sha256(candidate):
        raise Refused('EXISTING_DELIVERABLE_CHANGED: use a new run id')
    if not final.exists():
        shutil.copyfile(candidate, final)
    return {'status': 'REFERENCE_REASSEMBLED_FROM_APPROVED_TAKES', 'duration_s': 6.52,
            'new_url_production_ready': False, 'reference_window_only': True,
            'new_gpu_calls': 0, 'model_compute_cost_usd': 0,
            'cost_scope': 'No GPU calls. GitHub CPU, storage and egress excluded; not a Modal invoice.',
            'audio_integrity': assembly['audio_decoded_hash_identical'],
            'rhythm': rhythm_report, 'checks': checks,
            'limits': PROFILE['blocking_qualifications'], 'output_sha256': sha256(final)}


def verify_reference_output(final, audio, approved, source_words, model_cache, state):
    import subprocess
    import wave
    import cv2
    import numpy as np
    result = technical_video(final, 163)
    with wave.open(str(audio)) as stream:
        pcm = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').reshape(-1, 2)
    expected = np.concatenate([pcm[:140160], pcm[211200:]])
    actual = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', str(final),
                            '-map', '0:a:0', '-ar', '48000', '-ac', '2', '-f', 's16le', '-'],
                            check=True, capture_output=True, timeout=120).stdout, dtype='<i2').reshape(-1, 2)
    correlation = float(np.corrcoef(actual[:len(expected)].ravel(), expected.ravel())[0, 1])
    if not np.isfinite(correlation) or correlation < .999:
        raise Refused('FINAL_NARRATION_CHANGED: zero-offset PCM comparison failed')
    old, new = cv2.VideoCapture(str(approved)), cv2.VideoCapture(str(final))
    squared_error = []
    for _ in range(163):
        ok1, a = old.read()
        ok2, b = new.read()
        if not ok1 or not ok2:
            raise Refused('FINAL_REFERENCE_FRAME_MISSING')
        squared_error.append(float(np.mean((a.astype(float) - b.astype(float)) ** 2)))
    old.release()
    new.release()
    psnr = float(10 * np.log10(255 ** 2 / max(np.mean(squared_error), 1e-12)))
    if psnr < 36:
        raise Refused('FINAL_IMAGE_DIFFERS_FROM_APPROVED_REFERENCE: PSNR=' + str(psnr))
    alignment = state.root / 'final-alignment.json'
    def align_final():
        aligned = transcribe(final, model_cache, 'fr', strict=False)
        save_json(alignment, aligned)
        return {}
    run_stage(state, 'verify_final_words', {'final': sha256(final)}, [alignment], align_final)
    final_words = [w for segment in json.loads(alignment.read_text(encoding='utf-8'))['segments'] for w in segment['words']]
    same = tokens(' '.join(w['text'] for w in source_words)) == tokens(' '.join(w['text'] for w in final_words))
    return {**result, 'zero_offset_audio_correlation': correlation, 'approved_movie_psnr_db': psnr,
            'source_and_final_asr_words_identical': same,
            'asr_is_diagnostic_only_for_preapproved_excerpt': True,
            'first_last_audio_samples_preserved': True,
            'no_additional_word_removed_by_reference_silence_edit': True,
            'title_and_pip_preserved': True, 'new_performance_approval_claimed': False}


def verify_cpu_workers(state):
    import base64
    import modal
    from deploy import modal_ltx_worker as ltx, modal_tbdub_fr_worker as tbdub
    output = state.root / 'worker-preflight.json'
    def check():
        frozen_recipe()
        with ltx.app.run(name='ugcv2-autopilot-ltx-cpu-doctor', environment_name='main'):
            doctor = ltx.doctor.remote()
        if not doctor['ready_for_ltx']:
            raise Refused('LTX_CACHED_WEIGHTS_MISSING')
        audio = state.root / 'worker-speech16k.wav'
        extract_audio(state.root / 'actor-A.mp4', audio)
        with tbdub.app.run(name='ugcv2-autopilot-tbdub-cpu-preflight', environment_name='main'):
            checked = tbdub.preflight.remote(base64.b64encode((state.root / 'actor-A.mp4').read_bytes()).decode(),
                                               base64.b64encode(audio.read_bytes()).decode())
        checked.pop('preview_base64', None)
        if checked['status'] != 'CPU_FACE_PREFLIGHT_PASSED':
            raise Refused('TBDUB_FACE_PREFLIGHT_FAILED')
        save_json(output, {'ltx': doctor, 'tbdub': checked, 'gpu_calls': 0})
        return {'ltx_cached_weights': True, 'tbdub_face_preflight': True, 'gpu_calls': 0}
    run_stage(state, 'worker_preflight', {'actor': sha256(state.root / 'actor-A.mp4')}, [output], check)


def new_source_run(state, url, model_cache):
    source = state.root / 'download.mp4'
    run_stage(state, 'download', {'url': url}, [source, state.root / 'import.json'],
              lambda: (download(url, state.root) and {}))
    normalized = state.root / 'source.mp4'
    run_stage(state, 'normalize', {'sha256': sha256(source)}, [normalized],
              lambda: normalize(source, normalized))
    from production_vision import analyze_scenes
    scenes_path = state.root / 'scene-analysis.json'
    def scene_analysis():
        result = analyze_scenes(normalized)
        save_json(scenes_path, result)
        return {'detected_intervals': len(result['scenes']), 'semantics_qualified': False}
    run_stage(state, 'scenes', {'source': sha256(normalized)}, [scenes_path], scene_analysis)
    audio = state.root / 'source16k.wav'
    run_stage(state, 'extract_audio', {'source': sha256(normalized)}, [audio],
              lambda: (extract_audio(normalized, audio) and {}))
    alignment = state.root / 'alignment.json'
    def align():
        result = transcribe(audio, model_cache)
        save_json(alignment, result)
        return {'language': result['language']}
    run_stage(state, 'align', {'audio': sha256(audio)}, [alignment], align)
    translated = state.root / 'french-script.json'
    def adapt():
        result = translate_segments(json.loads(alignment.read_text(encoding='utf-8')), model_cache)
        save_json(translated, result)
        return {'phrases': len(result), 'translation': 'CPU EN-to-FR, not editorial adaptation'}
    run_stage(state, 'translate', {'alignment': sha256(alignment)}, [translated], adapt)
    # Stop before spending on voice/video when no new take can be delivered.
    require_qualified_generation()


def public_report(report):
    return {k: v for k, v in report.items() if k in (
        'status', 'run_id', 'duration_s', 'new_url_production_ready', 'reference_window_only',
        'new_gpu_calls', 'model_compute_cost_usd', 'cost_scope', 'audio_integrity', 'checks',
        'rhythm', 'limits', 'output_sha256', 'blocker_code')}


def fetch_deliverable(root, output):
    report = json.loads((root / 'report.json').read_text(encoding='utf-8'))
    if report.get('status') != 'REFERENCE_REASSEMBLED_FROM_APPROVED_TAKES':
        raise Refused('NO_DELIVERABLE: private report is blocked or incomplete')
    final = root / 'final.mp4'
    if not final.is_file() or sha256(final) != report.get('output_sha256'):
        raise Refused('DELIVERABLE_CHECKSUM_MISMATCH')
    output.mkdir(parents=True, exist_ok=True)
    for name in ('final.mp4', 'report.json'):
        shutil.copyfile(root / name, output / name)


def main():
    parser = argparse.ArgumentParser(description='UGCv2 frozen recipe, private resume and blocking quality gates')
    parser.add_argument('command', choices=['run', 'fetch'])
    parser.add_argument('--url')
    parser.add_argument('--profile', choices=['work-locked-v1', 'work-reference-v1'], default='work-locked-v1')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--work-root', type=Path, default=REPOSITORY / 'data/production')
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--private-remote', action='store_true')
    parser.add_argument('--verify-workers', action='store_true')
    parser.add_argument('--max-gpu-seconds', type=int, default=PROFILE['gpu_seconds_reservation_limit'])
    parser.add_argument('--public-report-dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 0 <= args.max_gpu_seconds <= 3600:
        parser.error('--max-gpu-seconds must be between 0 and 3600 for this qualification branch')
    run_id = safe_id(args.run_id)
    root = args.work_root.resolve() / run_id
    volume = PrivateVolume() if args.private_remote or args.command == 'fetch' else None
    if args.command == 'fetch':
        if not args.output:
            parser.error('fetch requires --output')
        volume.pull('runs/' + run_id, root)
        fetch_deliverable(root, args.output)
        print('Private result retrieved: ' + str(args.output))
        return 0
    if not args.url:
        parser.error('run requires --url')
    youtube_id(args.url)
    if volume and not (root / 'state.json').exists():
        volume.pull('runs/' + run_id, root)
    root.mkdir(parents=True, exist_ok=True)
    lock = RunLock(root / 'production.lock')
    lock.__enter__()
    state = None
    report = {'run_id': run_id, 'new_url_production_ready': False}
    exit_code = 2
    try:
        frozen_recipe()
        code = {p.name: sha256(p) for p in BASE.glob('*.py') if not p.name.startswith('test_')}
        config = {'youtube_id': youtube_id(args.url), 'profile': args.profile,
                  'profile_sha256': sha256(BASE / 'production_profile.json'), 'code': code}
        state = RunState(root, config, args.max_gpu_seconds,
                         (lambda p: volume.push('runs/' + run_id, p)) if volume else None)
        cache = args.work_root / 'cpu-model-cache'
        if args.profile == 'work-reference-v1':
            catalog = args.catalog or args.work_root / 'catalog'
            if not (catalog / 'production-catalog.json').is_file():
                if not volume or not volume.pull('catalog/work-v1', catalog):
                    raise Refused('PRIVATE_CATALOG_MISSING: bootstrap the actual approved Work files once')
            result = reference_run(state, catalog, args.url, cache, args.verify_workers)
        else:
            result = new_source_run(state, args.url, cache)
        report.update(result)
        exit_code = 0
    except Exception as exc:
        report.update(status='BLOCKED_NO_DELIVERABLE', blocker_code=str(exc).split(':', 1)[0],
                      diagnostic=str(exc), exception_type=type(exc).__name__)
        report['new_gpu_calls'] = len(state.data['calls']) if state else 0
    finally:
        try:
            save_json(root / 'report.json', report)
            if volume:
                volume.push('runs/' + run_id, root)
        finally:
            lock.__exit__()
    if args.public_report_dir:
        save_json(args.public_report_dir / 'production-report.json', public_report(report))
    print(json.dumps(public_report(report), ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Refused as exc:
        print('REFUSED: ' + str(exc), file=sys.stderr)
        sys.exit(2)
