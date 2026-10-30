import base64
import hashlib
import json
import sys
import time
from pathlib import Path

from production_state import save_json
from studio import Refused, command, sha256

ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = ROOT / 'productions/FR60-CONTINUITY-8S-20261030/recipe.json'
RECIPE_SHA = '2682d1012de4b90042725837faf0bd1af6580ad29637e7eb49ed4f7f409aa006'
sys.path.insert(0, str(ROOT))


def frozen_text_sha(path):
    # Approved receipts were recorded on Windows. Git checks the same source
    # out with LF on Linux; normalize only line endings, never source content.
    data = Path(path).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    return hashlib.sha256(data).hexdigest()


def frozen_recipe():
    if frozen_text_sha(RECIPE_PATH) != RECIPE_SHA:
        raise Refused('RECIPE_DRIFT: approved prompt or parameters changed')
    recipe = json.loads(RECIPE_PATH.read_text(encoding='utf-8'))
    for file, wanted in recipe['worker_files_sha256'].items():
        if frozen_text_sha(ROOT / file) != wanted:
            raise Refused('RECIPE_DRIFT: frozen worker changed: ' + file)
    return recipe


def model_call(state, key, worker, function, args, timeout):
    import modal
    if modal.Workspace.from_context().hydrate().name != 'lucj76861':
        raise Refused('Wrong Modal workspace')
    previous = state.data['calls'].get(key)
    if previous:
        if previous.get('call_id') and previous['status'] in ('RUNNING', 'RESULT_PENDING'):
            call = modal.FunctionCall.from_id(previous['call_id'])
            try:
                return call.get(timeout=timeout)
            except modal.exception.TimeoutError:
                raise Refused('REMOTE_CALL_PENDING: saved call is not resubmitted: ' + key)
        raise Refused('REMOTE_CALL_UNCERTAIN: reservation exists without reusable result; '
                      'inspect/cancel saved Modal call before an explicit bounded retry: ' + key)
    state.reserve(key, timeout)
    started = time.monotonic()
    with worker.app.run(name='ugcv2-production-' + key.replace('/', '-')[-50:], environment_name='main'):
        call = function.spawn(*args)
        state.data['calls'][key].update(status='RUNNING', call_id=call.object_id)
        state.flush()
        try:
            result = call.get(timeout=timeout)
        except BaseException:
            call.cancel(terminate_containers=True)
            state.data['calls'][key].update(status='CANCELLED_OR_FAILED',
                                           client_elapsed_s=round(time.monotonic() - started, 3))
            state.flush()
            raise
    state.data['calls'][key].update(status='RESULT_PENDING',
                                   client_elapsed_s=round(time.monotonic() - started, 3))
    state.flush()
    return result


def animate(state, take_id, anchor, attempt=1):
    from deploy import modal_ltx_worker as worker
    recipe = frozen_recipe()
    folder = state.root / 'takes' / take_id / str(attempt)
    folder.mkdir(parents=True, exist_ok=True)
    inputs = {'anchor': sha256(anchor), 'recipe': sha256(RECIPE_PATH)}
    stage = f'{take_id}/ltx/{attempt}'
    raw, normalized = folder / 'before-native.mp4', folder / 'before.mp4'
    if state.cached(stage, inputs):
        return raw, normalized
    payload = {'prompt': recipe['prompt'], 'duration_s': 4, 'aspect_ratio': '16:9',
               'seed': recipe['ltx_seed'], 'audio_mode': 'silent', 'image_strength': 1.0,
               'image_png_base64': base64.b64encode(Path(anchor).read_bytes()).decode(),
               'trace_id': f'production-{take_id}-{attempt}'}
    validated = worker.validate(payload)
    save_json(folder / 'graph.json', worker.build_graph(validated, output_prefix=payload['trace_id'],
                                                       uploaded_image='anchor.png'))
    result = model_call(state, stage, worker, worker.render_clip, (payload,), 900)
    metadata = result['metadata']
    if (metadata.get('seed') != recipe['ltx_seed'] or metadata.get('frames') != 97
            or metadata.get('model_revision') != recipe['ltx_reference_metadata']['model_revision']
            or metadata.get('comfyui_revision') != recipe['ltx_reference_metadata']['comfyui_revision']
            or metadata.get('continuity_mode') != 'image'):
        raise Refused('LTX_RESULT_RECIPE_DRIFT')
    raw.write_bytes(base64.b64decode(result['video_base64'], validate=True))
    command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', raw,
             '-vf', recipe['normalization'], '-t', '4', '-an', '-c:v', 'libx264',
             '-crf', '16', '-preset', 'fast', normalized])
    save_json(folder / 'ltx.json', metadata)
    state.data['calls'][stage]['status'] = 'SAVED'
    state.complete(stage, inputs, [raw, normalized, folder / 'ltx.json', folder / 'graph.json'])
    return raw, normalized


def continuation_anchor(raw, retained_frames, target):
    if not 1 <= retained_frames <= 100:
        raise Refused('Invalid retained frame count for four-second native master')
    # Same 24->25fps mapping as the accepted Work test: 100 retained frames
    # continue from native frame 95, not the unretained native frame 96.
    native_index = int((retained_frames - 1) * 24 / 25)
    command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', raw,
             '-vf', f'select=eq(n\\,{native_index})', '-frames:v', '1', target])
    return target


def synchronize(state, take_id, before, audio, attempt=1):
    from deploy import modal_tbdub_fr_worker as worker
    frozen_recipe()
    folder = state.root / 'takes' / take_id / str(attempt)
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / 'after.mp4'
    inputs = {'before': sha256(before), 'audio': sha256(audio), 'recipe': sha256(RECIPE_PATH)}
    stage = f'{take_id}/tbdub/{attempt}'
    if state.cached(stage, inputs):
        return output
    video64 = base64.b64encode(Path(before).read_bytes()).decode()
    audio64 = base64.b64encode(Path(audio).read_bytes()).decode()
    result = model_call(state, stage, worker, worker.render_student_four_seconds,
                        (video64, audio64), 600)
    output.write_bytes(base64.b64decode(result['video_base64'], validate=True))
    if sha256(output) != result['metadata']['video_sha256']:
        raise Refused('TBDUB_RESULT_CHECKSUM_MISMATCH')
    save_json(folder / 'tbdub.json', result['metadata'])
    state.data['calls'][stage]['status'] = 'SAVED'
    state.complete(stage, inputs, [output, folder / 'tbdub.json'])
    return output


def french_voice(state, blocks, batch_id='voice', attempt=1):
    from deploy import modal_chatterbox_v3_fr_pilot as worker
    if not 1 <= len(blocks) <= 7:
        raise Refused('VOICE_BATCH_LIMIT: existing worker supports 1-7 complete phrases')
    for block in blocks:
        if not 30 <= len(block['fr_text'].strip()) <= 310 or not 4 < block['end_s'] - block['start_s'] < 13:
            raise Refused('VOICE_BLOCK_UNSUPPORTED: existing V3 worker requires 30-310 characters and 4-13s source windows')
    stage = f'{batch_id}/v3/{attempt}'
    folder = state.root / batch_id / str(attempt)
    folder.mkdir(parents=True, exist_ok=True)
    if state.cached(stage, blocks):
        return json.loads((folder / 'voice.json').read_text(encoding='utf-8'))
    result = model_call(state, stage, worker, worker.render_original_paced_french_blocks, (blocks,), 1200)
    files = []
    for i, block in enumerate(result['blocks']):
        for take in block['candidates']:
            filename = folder / f'{i:03d}-{take["tag"]}.wav'
            filename.write_bytes(base64.b64decode(take.pop('wav_b64'), validate=True))
            if sha256(filename) != take['sha256']:
                raise Refused('VOICE_CHECKSUM_MISMATCH')
            take['path'] = filename.relative_to(state.root).as_posix()
            files.append(filename)
    save_json(folder / 'voice.json', result)
    state.data['calls'][stage]['status'] = 'SAVED'
    state.complete(stage, blocks, [*files, folder / 'voice.json'])
    return result
