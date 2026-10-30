import base64
import hashlib
import tempfile
from pathlib import Path

import modal

from deploy import modal_tbdub_fr_worker as existing

app = modal.App('ugcv2-source-performance-lips')


def inspect_cached_models(root):
    names = ['config.json', 'null_prompt_emb.pt', 'tbdub_student.safetensors', 'Wan2.2_VAE.safetensors',
             'hubert-large-ll60k/config.json', 'hubert-large-ll60k/preprocessor_config.json',
             'hubert-large-ll60k/pytorch_model.bin', 'face_landmarker.task']
    student = root/'tbdub_student.safetensors'
    if not student.is_file() or student.stat().st_size != existing.STUDENT_BYTES:
        raise RuntimeError('Student checkpoint size does not match the frozen recipe')
    result = {}
    for name in names:
        path = root/name
        if not path.is_file() or path.stat().st_size <= 100:
            raise RuntimeError('Missing cached model: ' + name)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b''):
                digest.update(chunk)
        stat = path.stat()
        result[name] = {'sha256': digest.hexdigest(), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
    if result['tbdub_student.safetensors']['sha256'] != existing.STUDENT_SHA256:
        raise RuntimeError('Student checkpoint SHA256 does not match the frozen recipe')
    if result['face_landmarker.task']['sha256'] != existing.LANDMARKER_SHA256:
        raise RuntimeError('Face landmarker SHA256 does not match the frozen recipe')
    return result


@app.function(image=existing.image, cpu=4, memory=16000, timeout=900,
              volumes={str(existing.MODEL_ROOT): existing.model_vol})
def verify_cached_models_cpu():
    return inspect_cached_models(existing.MODEL_ROOT)


@app.function(image=existing.image, gpu='L40S', cpu=8, memory=48000, timeout=1200,
              min_containers=0, max_containers=1, scaledown_window=2,
              volumes={str(existing.MODEL_ROOT): existing.model_vol})
def dub_source_shot(video_base64, audio_base64, duration_s, cache_receipt):
    if not 1 <= duration_s <= 15 or not existing._exists_check()['all_present']:
        raise RuntimeError('Unsupported source shot or missing existing cached Student weights')
    if cache_receipt.get('tbdub_student.safetensors', {}).get('sha256') != existing.STUDENT_SHA256:
        raise RuntimeError('No verified CPU checkpoint receipt')
    for name, record in cache_receipt.items():
        path = (existing.MODEL_ROOT/name).resolve()
        if not path.is_relative_to(existing.MODEL_ROOT.resolve()):
            raise RuntimeError('Invalid model receipt path')
        stat = path.stat()
        if (stat.st_size, stat.st_mtime_ns) != (record['bytes'], record['mtime_ns']):
            raise RuntimeError('Model cache changed after CPU verification: ' + name)
    with tempfile.TemporaryDirectory(prefix='ugcv2-source-lips-') as temp:
        folder = Path(temp)
        video, audio = existing._media_inputs(folder, video_base64, audio_base64)
        output = folder/'output'
        output.mkdir()
        existing._run_inference([
            '--video', str(video), '--audio', str(audio), '--inference-mode', 'student',
            '--num-student-steps', '2', '--sigma-shift', '1.0', '--motion-from-latents',
            '--seed', '42', '--checkpoint-dir', str(existing.MODEL_ROOT),
            '--sample-name', 'source-shot', '--output-dir', str(output),
            '--preprocess-report', str(folder/'preprocess.json')], timeout=1100, directory=folder)
        files = list(output.glob('*_tbdub.mp4'))
        if len(files) != 1:
            raise RuntimeError('Expected one official Student paste-back result')
        data = files[0].read_bytes()
        return {'video_base64': base64.b64encode(data).decode(),
                'metadata': {'engine': 'TBDub Student v1.1', 'upstream_sha': existing.UPSTREAM_SHA,
                             'student_steps': 2, 'sigma_shift': 1.0, 'seed': 42,
                             'motion_from_latents': True, 'sha256': hashlib.sha256(data).hexdigest(),
                             'duration_requested_s': duration_s, 'perceptual_qualified': False}}
