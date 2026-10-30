import json
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from production_state import RunState
from studio import Refused, command, probe, sha256, track
from source_media import composite_frame, mix_voice, validate_timeline
from source_production import cached_stage, require_qualifications, verify_recipe


def wav(path, seconds, value=1200):
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
        stream.writeframes(np.full(round(seconds * 48000), value, dtype='<i2').tobytes())
    return path


def timeline(frames=50):
    return {'source_sha256': 'a' * 64, 'frames': frames, 'fps': 25,
            'width': 100, 'height': 80,
            'shots': [{'id': 'one', 'start_frame': 0, 'end_frame': frames,
                       'mode': 'full'}]}


def test_completed_stage_is_not_recomputed(tmp_path):
    state = RunState(tmp_path, {}, 0)
    output = tmp_path / 'out.txt'
    count = []
    def operation():
        count.append(1)
        output.write_text('saved')
        return {'real': True}
    for _ in range(2):
        cached_stage(state, 'import', {'x': 1}, [output], operation)
    assert count == [1]


def test_failed_stage_resumes_without_repeating_upstream(tmp_path):
    state = RunState(tmp_path, {}, 0)
    first, second = tmp_path / 'first', tmp_path / 'second'
    cached_stage(state, 'import', {}, [first], lambda: first.write_text('ok'))
    with pytest.raises(RuntimeError):
        cached_stage(state, 'analyze', {}, [second], lambda: (_ for _ in ()).throw(RuntimeError('failure')))
    restored = RunState(tmp_path, {}, 0)
    cached_stage(restored, 'import', {}, [first], lambda: pytest.fail('repeated import'))
    cached_stage(restored, 'analyze', {}, [second], lambda: second.write_text('ok'))
    assert restored.cached('analyze', {})


@pytest.mark.parametrize('mutation', ['corrupt', 'missing', 'input'])
def test_invalid_cache_never_spends_again(tmp_path, mutation):
    state = RunState(tmp_path, {}, 0)
    output = tmp_path / 'out'
    cached_stage(state, 'face/one', {'x': 1}, [output], lambda: output.write_text('ok'))
    if mutation == 'corrupt':
        output.write_text('bad')
    elif mutation == 'missing':
        output.unlink()
    with pytest.raises(Refused):
        cached_stage(state, 'face/one', {'x': 2 if mutation == 'input' else 1}, [output],
                     lambda: pytest.fail('automatic GPU retry'))


def test_recipe_is_pinned_and_blocks_spending():
    recipe = verify_recipe()
    assert recipe['reference']['mp4_sha256'].startswith('346b8a25')
    assert recipe['motion_source'] == 'original_video'
    assert 'ltx' not in recipe['workers']
    with pytest.raises(Refused, match='QUALIFICATION_REQUIRED'):
        require_qualifications(recipe)


@pytest.mark.parametrize('key', ['identity', 'background', 'scene_layout', 'speaker', 'phonetic_lipsync'])
def test_each_missing_qualification_blocks(key):
    recipe = {'qualifications': {k: True for k in
              ['identity', 'background', 'scene_layout', 'speaker', 'phonetic_lipsync']}}
    recipe['qualifications'][key] = False
    with pytest.raises(Refused, match=key):
        require_qualifications(recipe)


def test_timeline_requires_exact_source_and_complete_coverage():
    data = timeline()
    validate_timeline(data, 'a' * 64, 50, 100, 80)
    with pytest.raises(Refused):
        validate_timeline(data, 'b' * 64, 50, 100, 80)
    data['shots'][0]['end_frame'] = 49
    with pytest.raises(Refused):
        validate_timeline(data, 'a' * 64, 50, 100, 80)


@pytest.mark.parametrize('rectangle', [[90, 0, 20, 30], [-1, 0, 20, 30], [0, 0, 0, 30]])
def test_pip_must_fit_source(rectangle):
    data = timeline()
    data['shots'][0].update(mode='pip', rectangle=rectangle)
    with pytest.raises(Refused):
        validate_timeline(data, 'a' * 64, 50, 100, 80)


def test_unknown_title_and_duplicate_shots_are_refused():
    data = timeline()
    data['shots'][0]['mode'] = 'title'
    with pytest.raises(Refused):
        validate_timeline(data, 'a' * 64, 50, 100, 80)
    data = timeline()
    data['shots'][0]['end_frame'] = 25
    data['shots'].append({**data['shots'][0], 'start_frame': 25, 'end_frame': 50})
    with pytest.raises(Refused):
        validate_timeline(data, 'a' * 64, 50, 100, 80)


def test_pip_composition_preserves_every_outside_pixel():
    source = np.arange(80 * 100 * 3, dtype=np.uint8).reshape(80, 100, 3)
    foreground = np.full((30, 20, 3), 111, np.uint8)
    background = np.full_like(foreground, 42)
    alpha = np.zeros((30, 20), np.float32)
    alpha[5:25, 5:15] = 1
    result = composite_frame(source, foreground, alpha, background, [70, 0, 20, 30])
    outside = np.ones(source.shape[:2], bool)
    outside[:30, 70:90] = False
    assert np.array_equal(result[outside], source[outside])
    assert (result[10:20, 75:85] == 111).all()
    assert (result[:5, 70:90] == 42).all()


@pytest.mark.parametrize('kind', ['nan', 'empty', 'opaque'])
def test_bad_matte_never_falls_back_to_original(kind):
    source = np.zeros((20, 20, 3), np.uint8)
    alpha = np.full((20, 20), {'nan': np.nan, 'empty': 0, 'opaque': 1}[kind], np.float32)
    with pytest.raises(Refused):
        composite_frame(source, source, alpha, source)


def test_voice_uses_real_samples_and_original_starts(tmp_path):
    a = wav(tmp_path / 'a.wav', .8)
    b = wav(tmp_path / 'b.wav', .8, 2400)
    output = tmp_path / 'mixed.wav'
    result = mix_voice([{'id': 'a', 'start_s': .2, 'end_s': 1.2, 'path': str(a)},
                        {'id': 'b', 'start_s': 1.5, 'end_s': 2.5, 'path': str(b)}], 3, output)
    with wave.open(str(output)) as stream:
        samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2')
    assert len(samples) == 144000
    assert (samples[:9600] == 0).all()
    assert (samples[10100:47000] == 1200).all()
    assert (samples[73000:109000] == 2400).all()
    assert result['audio_speed'] == 1


def test_voice_overflow_never_truncates_or_stretches(tmp_path):
    path = wav(tmp_path / 'long.wav', 1.1)
    with pytest.raises(Refused, match='VOICE_SLOT'):
        mix_voice([{'id': 'a', 'start_s': 0, 'end_s': 1, 'path': str(path)}], 2,
                  tmp_path / 'out.wav')
    assert not (tmp_path / 'out.wav').exists()


def test_voice_overlap_and_missing_file_are_refused(tmp_path):
    path = wav(tmp_path / 'voice.wav', .8)
    blocks = [{'id': 'a', 'start_s': 0, 'end_s': 1, 'path': str(path)},
              {'id': 'b', 'start_s': .9, 'end_s': 2, 'path': str(path)}]
    with pytest.raises(Refused):
        mix_voice(blocks, 2, tmp_path / 'out.wav')


def test_no_qualification_means_no_paid_adapter(tmp_path, monkeypatch):
    import source_production as pipeline
    monkeypatch.setattr(pipeline, 'synthesize', lambda *a: pytest.fail('paid synthesis invoked'))
    state = RunState(tmp_path, {}, 0)
    with pytest.raises(Refused, match='QUALIFICATION_REQUIRED'):
        pipeline.produce(state, tmp_path/'missing.mp4', {}, [], tmp_path, pipeline.verify_recipe())
    assert state.data['calls'] == {}


def test_remote_reservation_cannot_duplicate_billing(tmp_path):
    state = RunState(tmp_path, {}, 1200)
    state.reserve('identity/one/1', 1200)
    restored = RunState(tmp_path, {}, 1200)
    with pytest.raises(Refused, match='already reserved'):
        restored.reserve('identity/one/1', 1200)
    with pytest.raises(Refused, match='budget'):
        restored.reserve('identity/two/1', 1200)


def test_whole_budget_is_checked_before_any_paid_call(tmp_path):
    from source_production import validate_budget
    state = RunState(tmp_path, {}, 3600)
    with pytest.raises(Refused, match='GPU_BUDGET_PREFLIGHT'):
        validate_budget(state, [1], {'shots': [{'mode': 'full'}]})
    assert not state.data['calls']
    state = RunState(tmp_path/'enough', {}, 4200)
    assert validate_budget(state, [1], {'shots': [{'mode': 'full'}]}) == 4200


def test_fake_student_cache_is_rejected_on_cpu(tmp_path):
    from deploy.modal_source_lips import inspect_cached_models
    names = ['config.json', 'null_prompt_emb.pt', 'tbdub_student.safetensors', 'Wan2.2_VAE.safetensors',
             'hubert-large-ll60k/config.json', 'hubert-large-ll60k/preprocessor_config.json',
             'hubert-large-ll60k/pytorch_model.bin', 'face_landmarker.task']
    for name in names:
        path = tmp_path/name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b'x'*101)
    with pytest.raises(RuntimeError, match='Student'):
        inspect_cached_models(tmp_path)


def test_real_cpu_assembly_retains_frames_screen_pip_and_audio(tmp_path):
    from source_media import assemble_source
    source, clip, speech, output = [tmp_path/name for name in ('source.mp4', 'clip.mp4', 'speech.wav', 'output.mp4')]
    command(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=160x120:r=25:d=2',
             '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=2',
             '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', source])
    command(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=40x40:r=25:d=1',
             '-c:v', 'libx264', '-pix_fmt', 'yuv420p', clip])
    wav(speech, 2, 5000)
    data = {'source_sha256': sha256(source), 'frames': 50, 'fps': 25, 'width': 160, 'height': 120,
            'shots': [{'id': 'screen', 'start_frame': 0, 'end_frame': 25, 'mode': 'screen'},
                      {'id': 'pip', 'start_frame': 25, 'end_frame': 50, 'mode': 'pip', 'rectangle': [120, 0, 40, 40]}]}
    validate_timeline(data, sha256(source), 50, 160, 120)
    result = assemble_source(source, speech, data, {'pip': clip}, output)
    assert result['frames'] == 50
    command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', output, '-f', 'null', '-'])
    import cv2
    cap = cv2.VideoCapture(str(output))
    for index in range(50):
        ok, frame = cap.read()
        assert ok
        assert frame[80, 80, 0] > 240
        if index < 25:
            assert frame[20, 140, 0] > 240
        else:
            assert frame[20, 140, 2] > 240
    cap.release()
    assert track(probe(output), 'audio')['codec_name'] == 'aac'
