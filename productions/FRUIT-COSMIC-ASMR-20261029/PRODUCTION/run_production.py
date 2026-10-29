import argparse
import base64
import hashlib
import json
import math
import os
import random
import signal
import subprocess
import sys
import time
import wave
from array import array
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'productions/PORTFOLIO-PREMIUM-12-2026-10-27/PRODUCTION'))
from run_campaign import command, now, probe, save
from deploy.modal_ltx_worker import validate


def check():
    plan = json.loads((ROOT / 'PRODUCTION_PLAN.json').read_text(encoding='utf-8'))
    if (plan['workspace'], plan['app'], plan['function'], plan['attempts_per_shot'], plan['max_concurrent_gpu']) != ('lucj76861', 'pvs-ltx', 'render_clip', 1, 1):
        raise ValueError('Compte ou garde-fous invalides')
    if [s['id'] for s in plan['shots']] != ['01', '02', '03']:
        raise ValueError('Trois plans exactement sont requis')
    for shot in plan['shots']:
        path = ROOT / shot['image']
        if hashlib.sha256(path.read_bytes()).hexdigest() != shot['image_sha256']:
            raise ValueError('Image modifiée : ' + str(path))
        with Image.open(path) as image:
            image.load()
            if image.format != 'PNG' or image.size != (768, 1344):
                raise ValueError('PNG initial incompatible')
        payload = json.loads((ROOT / shot['payload']).read_text())
        if payload['duration_s'] != 5 or payload['aspect_ratio'] != '9:16' or payload['audio_mode'] != 'silent':
            raise ValueError('Paramètres hors mission')
        validate(dict(payload, image_png_base64=base64.b64encode(path.read_bytes()).decode()))
    audio = ROOT / 'ASSETS/asmr-original.wav'
    if hashlib.sha256(audio.read_bytes()).hexdigest() != plan['audio_sha256']:
        raise ValueError('Audio modifié')
    with wave.open(str(audio), 'rb') as source:
        if (source.getnchannels(), source.getframerate(), source.getnframes()) != (2, 48000, 720000):
            raise ValueError('Audio incompatible')
    return plan


def remote_preflight(plan):
    import modal
    if modal.Workspace.from_context().hydrate().name != 'lucj76861':
        raise ValueError('Workspace inattendu, aucun GPU autorisé')
    volume = modal.Volume.from_name('studio-ltx25-models', create_if_missing=False).hydrate()
    actual = {}
    for folder in ('diffusion_models', 'text_encoders', 'vae', 'latent_upscale_models'):
        actual.update({entry.path.lstrip('/'): entry.size for entry in volume.listdir('/' + folder)})
    for path, size in plan['existing_models'].items():
        if actual.get(path) != size:
            raise ValueError('Modèle existant absent ou modifié : ' + path)
    function = modal.Function.from_name('pvs-ltx', 'render_clip', environment_name='main').hydrate()
    if function.object_id != plan['existing_function_id']:
        raise ValueError('Fonction distante différente de la fonction inspectée')
    stats = function.get_current_stats()
    if stats.num_running_inputs or stats.backlog:
        raise ValueError('LTX occupé, arrêt sans mise en concurrence')
    return function


def render(confirm):
    plan = check()
    if confirm != 'oui' or os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        raise ValueError('Calcul non autorisé ou relance interdite')
    for shot in plan['shots']:
        if (ROOT / f"REPORTS/shot-{shot['id']}-receipt.json").exists() or (ROOT / f"RENDERS/shot-{shot['id']}.mp4").exists():
            raise ValueError('Tentative existante, régénération interdite')
    function = remote_preflight(plan)
    for folder in ('REPORTS', 'RENDERS', 'EXPORTS'):
        (ROOT / folder).mkdir(exist_ok=True)

    def interrupted(signum, frame):
        raise KeyboardInterrupt('Interruption demandée')

    signal.signal(signal.SIGTERM, interrupted)
    for shot in plan['shots']:
        stats = function.get_current_stats()
        if stats.num_running_inputs or stats.backlog:
            raise ValueError('LTX occupé avant la prise suivante')
        payload = json.loads((ROOT / shot['payload']).read_text())
        payload['image_png_base64'] = base64.b64encode((ROOT / shot['image']).read_bytes()).decode()
        receipt_path = ROOT / f"REPORTS/shot-{shot['id']}-receipt.json"
        receipt = {'status': 'starting', 'at': now(), 'shot': shot['id'], 'workspace': 'lucj76861',
                   'image_sha256': shot['image_sha256'], 'github_run_id': os.environ.get('GITHUB_RUN_ID'), 'attempt': 1}
        save(receipt_path, receipt)
        call = None
        completed = False
        try:
            call = function.spawn(payload)
            receipt.update(status='running', call_id=call.object_id)
            save(receipt_path, receipt)
            result = call.get(timeout=600)
            completed = True
            raw = base64.b64decode(result['video_base64'], validate=True)
            path = ROOT / f"RENDERS/shot-{shot['id']}.mp4"
            path.write_bytes(raw)
            receipt.update(metadata=result['metadata'], sha256=hashlib.sha256(raw).hexdigest())
            info = probe(path)
            video = next(s for s in info['streams'] if s['codec_type'] == 'video')
            if (video['width'], video['height']) != (768, 1344) or abs(float(info['format']['duration']) - 121/24) > .12:
                raise ValueError('Vrai rendu incompatible')
            if result['metadata'].get('continuity_mode') != 'image':
                raise ValueError('Conditionnement image non attesté')
            command(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'])
            receipt.update(status='technical_pass_visual_review_pending', at=now())
        except BaseException as error:
            receipt.update(status='failed', error=str(error), at=now())
            raise
        finally:
            if call is not None and not completed:
                try:
                    call.cancel(terminate_containers=True)
                    receipt['cancellation_requested_at'] = now()
                except Exception as error:
                    receipt['cancellation_error'] = str(error)
            save(receipt_path, receipt)


def cancel():
    import modal
    if modal.Workspace.from_context().hydrate().name != 'lucj76861':
        raise ValueError('Workspace inattendu')
    for path in (ROOT / 'REPORTS').glob('shot-*-receipt.json'):
        receipt = json.loads(path.read_text())
        if receipt.get('call_id') and receipt['status'] in ('starting', 'running', 'failed'):
            modal.FunctionCall.from_id(receipt['call_id']).cancel(terminate_containers=True)


def foley(path, cues):
    rate = 48000
    samples = [0.0] * (15 * rate)
    rng = random.Random(20261029)
    for start, gain, length in [(4.55, .035, .3)] + [(t, .26 if i == 0 else .19, .58) for i, t in enumerate(cues)]:
        for i in range(round(length * rate)):
            t = i / rate
            attack = min(1, t * 2400)
            noise = rng.uniform(-1, 1)
            crack = noise * math.exp(-t * 160)
            ring = sum(a * math.sin(2 * math.pi * f * t) * math.exp(-t * decay)
                       for a, f, decay in [(1, 1807, 15), (.58, 2941, 19), (.3, 4517, 24), (.12, 7139, 32)])
            index = round(start * rate) + i
            if index < len(samples):
                samples[index] += gain * attack * (.62 * crack + .38 * ring)
    pcm = array('h')
    for i, value in enumerate(samples):
        fade = min(1, i / 480, (len(samples) - 1 - i) / 480)
        level = round(max(-.95, min(.95, value * fade)) * 32767)
        pcm.extend((level, round(level * .97)))
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())


def motion_cues(path, windows):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', 'fps=24,scale=64:112,format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True, check=True, timeout=120).stdout
    size = 64 * 112
    frames = [raw[i:i+size] for i in range(0, len(raw), size)]
    cues = []
    for low, high in windows:
        indices = range(max(1, math.ceil(low * 24)), min(len(frames), math.floor(high * 24) + 1))
        best = max(indices, key=lambda i: sum(abs(a-b) for a, b in zip(frames[i], frames[i-1])))
        cues.append(best / 24)
    return cues


def assemble():
    plan = check()
    edit = ROOT / 'REPORTS/EDIT'
    edit.mkdir(parents=True, exist_ok=True)
    (ROOT / 'EXPORTS').mkdir(exist_ok=True)
    clips = []
    for shot in plan['shots']:
        source = ROOT / f"RENDERS/shot-{shot['id']}.mp4"
        receipt = json.loads((ROOT / f"REPORTS/shot-{shot['id']}-receipt.json").read_text())
        if receipt['status'] != 'technical_pass_visual_review_pending' or receipt['sha256'] != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError('Rendu réel vérifié manquant')
        target = edit / f"shot-{shot['id']}.mp4"
        command(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-t', '5', '-an', '-vf',
                 'fps=24,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p',
                 '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', str(target)])
        clips.append(target)
    listing = edit / 'concat.txt'
    listing.write_text(''.join("file '" + str(p.resolve().as_posix()) + "'\n" for p in clips), encoding='utf-8')
    picture = edit / 'picture.mp4'
    command(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', str(picture)])
    cues = [5 + t for t in motion_cues(clips[1], [(1.1, 2.1)])]
    cues += [10 + t for t in motion_cues(clips[2], [(.65, 1.3), (1.8, 2.5), (3.05, 3.75)])]
    audio = edit / 'asmr-synchronized.wav'
    foley(audio, cues)
    save(ROOT / 'REPORTS/AUDIO_CUES.json', {'cue_times_s': cues, 'method': 'strongest frame motion within planned cutting windows',
         'review': 'heuristic alignment; human listening and visual review pending', 'native_audio_used': False})
    output = ROOT / 'EXPORTS/FRAISE-COSMIQUE-ASMR-1080x1920.mp4'
    command(['ffmpeg', '-v', 'error', '-y', '-i', str(picture), '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0',
             '-c:v', 'copy', '-af', 'loudnorm=I=-18:TP=-2:LRA=7', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
             '-ac', '2', '-t', '15', '-movflags', '+faststart', str(output)])
    info = probe(output)
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    audio_info = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    if (video['width'], video['height'], int(video['nb_frames']), video['codec_name'], video['pix_fmt']) != (1080, 1920, 360, 'h264', 'yuv420p'):
        raise ValueError('Format vidéo final incorrect')
    if abs(float(info['format']['duration']) - 15) > .05 or audio_info['sample_rate'] != '48000' or audio_info['codec_name'] != 'aac':
        raise ValueError('Durée ou format audio incorrect')
    command(['ffmpeg', '-v', 'error', '-xerror', '-i', str(output), '-f', 'null', '-'])
    save(ROOT / 'REPORTS/FINAL.json', {'status': 'real_render_technical_pass_review_pending', 'probe': info,
         'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'publish': False, 'native_resolution': '768x1344',
         'review': 'Artistic continuity, cut accuracy and ASMR listening are not validated automatically.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['check', 'preflight', 'render', 'assemble', 'cancel'])
    parser.add_argument('--confirm-spend', default='non')
    args = parser.parse_args()
    if args.phase == 'check':
        check()
        print('Three PNGs, payloads, audio and guards checked; no remote compute.')
    elif args.phase == 'preflight':
        remote_preflight(check())
        print('lucj76861, deployed function, five existing weights and idle state verified; no compute.')
    elif args.phase == 'render':
        render(args.confirm_spend)
    elif args.phase == 'assemble':
        assemble()
    else:
        cancel()
