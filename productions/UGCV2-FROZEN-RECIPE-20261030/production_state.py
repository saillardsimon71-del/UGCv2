import hashlib
import json
import os
import re
from pathlib import Path

from studio import Refused, sha256


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.partial')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class RunState:
    def __init__(self, root, config, max_gpu_seconds=1800, checkpoint=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'state.json'
        self.checkpoint = checkpoint
        key = fingerprint({'config': config, 'max_gpu_seconds': max_gpu_seconds})
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding='utf-8'))
            if self.data['configuration'] != key:
                raise Refused('Run configuration changed; use a new run id')
        else:
            self.data = {'schema': 'ugcv2.run/v1', 'configuration': key,
                         'stages': {}, 'calls': {}, 'max_gpu_seconds': max_gpu_seconds}
            self.flush()

    def flush(self):
        save_json(self.path, self.data)
        if self.checkpoint:
            self.checkpoint(self.root)

    def cached(self, stage, inputs):
        record = self.data['stages'].get(stage)
        if not record:
            return False
        if record['inputs'] != fingerprint(inputs):
            raise Refused(stage + ': inputs changed; do not reuse a stale take')
        for name, digest in record['files'].items():
            file = self.root / name
            if not file.is_file() or sha256(file) != digest:
                raise Refused(stage + ': missing file or checksum mismatch: ' + name)
        return True

    def complete(self, stage, inputs, outputs, report=None):
        files = {str(Path(p).resolve().relative_to(self.root)).replace('\\', '/'): sha256(p)
                 for p in outputs}
        self.data['stages'][stage] = {'inputs': fingerprint(inputs), 'files': files,
                                     'report': report or {}}
        self.flush()

    def reserve(self, call_key, seconds):
        if call_key in self.data['calls']:
            raise Refused(call_key + ': already reserved; resume the saved call, never resubmit blindly')
        spent = sum(c['reserved_seconds'] for c in self.data['calls'].values())
        if seconds <= 0 or spent + seconds > self.data['max_gpu_seconds']:
            raise Refused('GPU budget exhausted before submission')
        self.data['calls'][call_key] = {'status': 'RESERVED', 'reserved_seconds': seconds}
        self.flush()


class RunLock:
    def __init__(self, path):
        self.path = Path(path)

    def __enter__(self):
        self.stream = self.path.open('a+b')
        if self.stream.tell() == 0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise Refused('RUN_LOCKED: another execution owns this run') from None
        return self

    def __exit__(self, *exc):
        self.stream.close()


def safe_id(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
        raise Refused('Run id: use 1-80 letters, digits, underscores or hyphens')
    return value


class PrivateVolume:
    def __init__(self, name='ugcv2-production-private'):
        import modal
        if modal.Workspace.from_context().hydrate().name != 'lucj76861':
            raise Refused('Wrong Modal workspace; expected lucj76861')
        self.volume = modal.Volume.from_name(name, create_if_missing=False)
        self.uploaded = {}

    def pull(self, prefix, destination):
        destination = Path(destination).resolve()
        prefix = prefix.strip('/') + '/'
        try:
            entries = list(self.volume.iterdir(prefix, recursive=True))
        except Exception as exc:
            if type(exc).__name__ == 'NotFoundError':
                return False
            raise
        for entry in entries:
            if getattr(entry.type, 'name', '') != 'FILE':
                continue
            name = entry.path.lstrip('/')
            if not name.startswith(prefix):
                raise Refused('Private volume returned an unexpected path')
            target = (destination / name[len(prefix):]).resolve()
            if not target.is_relative_to(destination):
                raise Refused('Private storage path traversal')
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('wb') as stream:
                for chunk in self.volume.read_file(entry.path):
                    stream.write(chunk)
        return bool(entries)

    def push(self, prefix, root):
        root = Path(root)
        # Upload data first and the journal last, so a visible receipt never
        # points to bytes that have not yet reached private storage.
        files = [p for p in root.rglob('*') if p.is_file()
                 and not p.name.endswith(('.partial', '.lock')) and p.name != 'state.json']
        changed = [(file, '/' + prefix.strip('/') + '/' + file.relative_to(root).as_posix(), sha256(file))
                   for file in files]
        changed = [(file, remote, digest) for file, remote, digest in changed
                   if self.uploaded.get(remote) != digest]
        if changed:
            with self.volume.batch_upload(force=True) as batch:
                for file, remote, digest in changed:
                    batch.put_file(file, remote)
            self.uploaded.update({remote: digest for _, remote, digest in changed})
        if (root / 'state.json').exists():
            with self.volume.batch_upload(force=True) as batch:
                batch.put_file(root / 'state.json', '/' + prefix.strip('/') + '/state.json')
