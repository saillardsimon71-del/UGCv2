import modal
from deploy import modal_chatterbox_v3_fr_pilot as reference

app = modal.App('ugcv2-work-four-second-voice-diagnostic')


@app.function(image=reference.image, serialized=True, gpu='L40S', cpu=6, memory=24000,
              timeout=900, min_containers=0, max_containers=1, scaledown_window=2,
              volumes={str(reference.VOICE_ROOT): reference.voice_volume})
def speak_once(text):
    import base64
    import hashlib
    import os
    import tempfile
    import time
    from pathlib import Path

    if not 10 <= len(text.strip()) <= 100 or any(c in text for c in '\x00<>'):
        raise ValueError('One plain short French utterance required')
    os.environ['HF_HOME'] = '/mnt/ugcv2_chatterbox_v3_cache/hf'
    os.environ['XDG_CACHE_HOME'] = '/mnt/ugcv2_chatterbox_v3_cache/cache'
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    snapshot = Path('/mnt/ugcv2_chatterbox_v3_cache/hf/hub/models--ResembleAI--chatterbox/refs/main').read_text().strip()
    if snapshot != '5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18':
        raise RuntimeError('Reference voice checkpoint snapshot changed')
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    started = time.monotonic()
    model = ChatterboxMultilingualTTS.from_pretrained(device='cuda', t3_model='v3')
    torch.manual_seed(60100)
    wav = model.generate(text, language_id='fr', audio_prompt_path=None,
                         exaggeration=.43, cfg_weight=.63, temperature=.77)
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / 'voice.wav'
        torchaudio.save(str(output), wav.cpu(), model.sr)
        data = output.read_bytes()
    return {'audio_base64': base64.b64encode(data).decode(),
            'metadata': {'engine': 'Chatterbox Multilingual V3',
                         'upstream_sha': '5de7a54aa4e5e2baadb0182dde554908b48b85c2',
                         'checkpoint_snapshot': snapshot,
                         'seed': 60100, 'exaggeration': .43, 'cfg_weight': .63,
                         'temperature': .77, 'audio_prompt_path': None,
                         'conditioning': 'reference builtin default voice',
                         'duration_s': float(wav.shape[-1] / model.sr),
                         'sample_rate': model.sr, 'sha256': hashlib.sha256(data).hexdigest(),
                         'wall_seconds': round(time.monotonic() - started, 3),
                         'candidates_generated': 1, 'model_downloads_allowed': False}}
