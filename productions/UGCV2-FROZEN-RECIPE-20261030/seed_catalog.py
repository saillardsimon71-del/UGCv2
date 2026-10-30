import argparse
import json
import shutil
from pathlib import Path

from assets import init
from production_state import PrivateVolume, save_json
from studio import Refused, command, sha256

HYBRID_SHA = '346b8a25aa0722094f57e51aef3d41a97e1966f7ad1d04c4517c8fbbe5b7297d'
REFERENCES = {
    'FR60-PRESENTER-PROOF-20261030/ASSETS/presenter-studio.png':
        'bd5ce8b0b67fd7cae6f197fc4608e7dff8b78882c162aba54c9e177d6e37bea3',
    'FR60-PRESENTER-PROOF-20261030/CACHE/presenter-i2v.mp4':
        '8ed4ba8dd5822dfd33bd366699f87a75e7bc59a81fe60da2c833894f8fc47c1b',
    'FR60-PRESENTER-PROOF-20261030/CACHE/presenter-master.mp4':
        'a4395b9b9cf78e3de1dbca39db5b13fe970c1f1f955ca2b154723f6c4cae634b',
    'FR60-PRESENTER-PROOF-20261030/EXPORTS/Clip_A_gros_plan.mp4':
        '3bbe9bec2e127178d5b944602cfff6fc16536a635568e686537154a6f5e82ba2',
    'FR60-PRESENTER-PROOF-20261030/EXPORTS/Clip_B_PiP.mp4':
        '9636954842f8e37f10751320b565ed7f0f23c498f648641bdd9143a11357504f',
    'FR60-PRESENTER-PROOF-20261030/CACHE/A-tbdub.mp4':
        '84f0f7d393f6c04f84f4a119af9181c0a2c801bf5771fe8af48fab3f0a2fff68',
    'FR60-CONTINUITY-8S-20261030/CACHE/trial-1-montage-4s.mp4':
        '7483f719139370a2a39152b47670d47b9fa877ab1f8de61a31c6dbda4e6b9185',
}


def seed(work_root, hybrid, work_zip, approved, target):
    if sha256(hybrid) != HYBRID_SHA:
        raise Refused('Reference source differs from original Work hybrid')
    for name, wanted in REFERENCES.items():
        if sha256(work_root / 'productions' / name) != wanted:
            raise Refused('Reference changed: ' + name)
    init(work_zip, approved, target)
    for name in REFERENCES:
        output = target / name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(work_root / 'productions' / name, output)
    source = target / 'reference-source-8s.mp4'
    command(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-ss', '7.6', '-i', hybrid,
             '-t', '8', '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'libx264', '-crf', '16',
             '-preset', 'fast', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
             '-movflags', '+faststart', source])
    files = {p.relative_to(target).as_posix(): sha256(p) for p in target.rglob('*') if p.is_file()}
    save_json(target / 'production-catalog.json', {
        'schema': 'ugcv2.production-catalog/v1', 'files': files,
        'source': {'path': source.name, 'sha256': sha256(source)},
        'youtube_id': 'KSOxkhWs2Ic', 'youtube_window_s': [49.6, 57.6],
        'hybrid_parent_sha256': HYBRID_SHA,
        'reference_only': True, 'approved_native_master_present': True,
        'no_generated_take_may_be_approved_by_matching_seed': True,
        'montage': {'full': [0, 110], 'title': [110, 166], 'pip': [166, 199],
                    'screen': [199, 200], 'rectangle': [1428, 0, 492, 444]},
        'privacy': 'Authenticated Modal volume only; no public audiovisual artifacts',
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='One-time private bootstrap from actual approved Work files')
    parser.add_argument('--work-root', type=Path, required=True)
    parser.add_argument('--hybrid', type=Path, required=True)
    parser.add_argument('--work-zip', type=Path, required=True)
    parser.add_argument('--approved-mp4', type=Path, required=True)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    seed(args.work_root, args.hybrid, args.work_zip, args.approved_mp4, args.target)
    if args.upload:
        import modal
        if modal.Workspace.from_context().hydrate().name != 'lucj76861':
            raise Refused('Wrong Modal workspace')
        modal.Volume.from_name('ugcv2-production-private', create_if_missing=True).hydrate()
        PrivateVolume().push('catalog/work-v1', args.target)
    print(json.dumps({'catalog': str(args.target), 'private_uploaded': args.upload, 'gpu_calls': 0}))
