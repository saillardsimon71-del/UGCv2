import json
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from production_state import RunState
from studio import Refused, sha256


class DiagnosticTests(unittest.TestCase):
    def audio(self, root, seconds):
        path = root / 'utterance.wav'
        pcm = np.zeros((round(seconds * 48000), 2), dtype='<i2')
        pcm[100:-100] = 2000
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            stream.writeframes(pcm.tobytes())
        return path, pcm

    def test_whole_utterance_is_padded_without_losing_any_sample(self):
        from production_diagnostic import pad_utterance
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            voice, expected = self.audio(root, 3.2)
            report = pad_utterance(voice, root / 'four.wav')
            with wave.open(str(root / 'four.wav')) as stream:
                actual = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').reshape(-1, 2)
            self.assertEqual(len(actual), 192000)
            np.testing.assert_array_equal(actual[3840:3840 + len(expected)], expected)
            self.assertTrue(report['all_utterance_samples_preserved'])
            self.assertFalse(report['speed_changed'])

    def test_overlong_voice_stops_instead_of_truncating(self):
        from production_diagnostic import pad_utterance
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            voice, _ = self.audio(root, 3.9)
            with self.assertRaisesRegex(Refused, 'VOICE_DOES_NOT_FIT_FOUR_SECONDS'):
                pad_utterance(voice, root / 'four.wav')
            self.assertFalse((root / 'four.wav').exists())

    def test_one_ltx_and_one_tbdub_across_all_attempt_ids(self):
        with tempfile.TemporaryDirectory() as td:
            state = RunState(Path(td), {}, max_gpu_seconds=3600)
            state.data['call_limits'] = {'ltx': 1, 'tbdub': 1}
            state.flush()
            state.reserve('new4s/ltx/1', 900)
            state.reserve('new4s/tbdub/1', 600)
            with self.assertRaisesRegex(Refused, 'GPU_CALL_LIMIT_REACHED'):
                state.reserve('new4s/ltx/2', 900)
            resumed = RunState(Path(td), {}, max_gpu_seconds=3600)
            with self.assertRaisesRegex(Refused, 'GPU_CALL_LIMIT_REACHED'):
                resumed.reserve('other/tbdub/2', 600)

    def test_diagnostic_requires_explicit_private_retrieval(self):
        from production import fetch_deliverable
        from production_diagnostic import fetch_diagnostic
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            movie = root / 'diagnostic-4s.mp4'
            movie.write_bytes(b'diagnostic bytes')
            report = {'status': 'DIAGNOSTIC_PRIVATE_UNVALIDATED', 'publish_allowed': False,
                      'diagnostic_files': {movie.name: sha256(movie)}}
            (root / 'report.json').write_text(json.dumps(report))
            with self.assertRaises(Refused):
                fetch_deliverable(root, root / 'normal')
            fetch_diagnostic(root, root / 'private')
            self.assertEqual((root / 'private' / movie.name).read_bytes(), movie.read_bytes())
            report['publish_allowed'] = True
            (root / 'report.json').write_text(json.dumps(report))
            with self.assertRaises(Refused):
                fetch_diagnostic(root, root / 'unsafe')


if __name__ == '__main__':
    unittest.main()
