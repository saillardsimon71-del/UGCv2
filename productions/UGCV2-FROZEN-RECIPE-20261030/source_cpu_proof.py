import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from production_state import save_json
from source_media import extract_shot, replace_background
from source_production import ROOT, verify_recipe
from studio import Refused, command, probe, sha256, track


def run(reference, output):
    recipe = verify_recipe()
    master = reference/'UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4'
    if sha256(master) != recipe['reference']['mp4_sha256']:
        raise Refused('REFERENCE_SHA_MISMATCH')
    command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', master, '-f', 'null', '-'], timeout=240)
    details = json.loads((reference/'tbdub_result.json').read_text(encoding='utf-8'))
    for sample in details['samples']:
        if sample['status'] != 'real_tbdub_mp4' or sha256(reference/sample['filename']) != sample['sha256']:
            raise Refused('REFERENCE_SHOT_SHA_MISMATCH')
    output.mkdir(parents=True, exist_ok=True)
    before, after, alpha = [output/name for name in ('before-4s.mp4', 'background-4s.mp4', 'alpha-4s.mkv')]
    extract_shot(reference/'cam_a_source_face.mp4',
                 {'start_frame': 10, 'end_frame': 110, 'mode': 'full'}, before)
    matte_report = replace_background(before, ROOT/recipe['background']['path'], after, alpha)
    a, b, masks = [cv2.VideoCapture(str(p)) for p in (before, after, alpha)]
    subject_errors, background_changes = [], []
    for index in range(100):
        ok_a, old = a.read()
        ok_b, new = b.read()
        ok_m, mask = masks.read()
        if not (ok_a and ok_b and ok_m):
            raise Refused('PROOF_FRAME_MISSING')
        diff = np.abs(old.astype(np.float32)-new.astype(np.float32)).mean(axis=2)
        subject, backdrop = mask[:, :, 0] >= 254, mask[:, :, 0] <= 1
        if subject.sum() < 1000 or backdrop.sum() < 1000:
            raise Refused('PROOF_ALPHA_NO_MEASURABLE_REGIONS')
        subject_errors.append(float(diff[subject].mean()))
        background_changes.append(float(diff[backdrop].mean()))
        if index == 50:
            cv2.imwrite(str(output/'before.jpg'), old)
            cv2.imwrite(str(output/'after.jpg'), new)
    for capture in (a, b, masks):
        capture.release()
    error, change = float(np.mean(subject_errors)), float(np.mean(background_changes))
    if error > 5 or change < 10:
        raise Refused(f'PROOF_COMPOSITE_REGRESSION: foreground MAE={error}, background change={change}')
    command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', after, '-f', 'null', '-'])
    return {'schema': 'ugcv2.source-cpu-proof/v1', 'reference_sha256': sha256(master),
            'reference_frames': int(track(probe(master), 'video')['nb_frames']),
            'reference_shot_hashes_checked': len(details['samples']),
            'diagnostic_frames': 100, 'diagnostic_duration_s': 4,
            'foreground_mae_inside_opaque_mask': error, 'background_mean_change': change,
            'matte': matte_report, 'background_sha256': recipe['background']['sha256'],
            'output_sha256': sha256(after), 'alpha_sha256': sha256(alpha),
            'full_decode': True, 'gpu_calls': 0, 'new_60s_render': False,
            'new_identity_render': False, 'new_lipsync_render': False,
            'naturalness_or_identity_certified': False,
            'scope': 'CPU composition on four existing seconds; not a production qualification'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.reference_dir, args.output)
    save_json(args.report, result)
    print(json.dumps(result, indent=2))
