import json
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from production_state import RunState
from studio import Refused, sha256


class DiagnosticTests(unittest.TestCase):
    def approved_fixture(self, parent):
        from production_diagnostic import PROFILE, pad_utterance
        root = parent / PROFILE['mission_run_id']
        root.mkdir()
        pcm_file, _ = self.audio(root, 1.84)
        pcm_file.rename(root / 'new-voice48k-whole.wav')
        import shutil
        shutil.copyfile(root / 'new-voice48k-whole.wav', root / 'new-voice-native.wav')
        pad_utterance(root / 'new-voice48k-whole.wav', root / 'new-voice-4s.wav')
        shutil.copyfile(root / 'new-voice-native.wav', root / 'new-speech16k.wav')
        text = 'Le déclencheur est le tout premier.'
        asr = {'segments': [{'text': 'Le décanseur est le tout preni.', 'words': [
            {'text': 'Le', 'start_s': 0., 'end_s': .24},
            {'text': 'décanseur', 'start_s': .24, 'end_s': .76},
            {'text': 'est', 'start_s': .76, 'end_s': .84},
            {'text': 'le', 'start_s': .84, 'end_s': .94},
            {'text': 'tout', 'start_s': .94, 'end_s': 1.06},
            {'text': 'preni.', 'start_s': 1.06, 'end_s': 1.34}]}]}
        (root / 'new-alignment.json').write_text(json.dumps(asr), encoding='utf-8')
        (root / 'new-script.json').write_text(json.dumps({'fr_text': text}), encoding='utf-8')
        approval = {'schema': 'ugcv2.human-voice-approval/v1', 'run_id': root.name,
                    'authority': 'explicit_user_validation_in_current_chat', 'expected_text': text,
                    'native_wav_sha256': sha256(root / 'new-voice-native.wav'),
                    'whole_pcm_sha256': sha256(root / 'new-voice48k-whole.wav'),
                    'padded_wav_sha256': sha256(root / 'new-voice-4s.wav'),
                    'speech16k_sha256': sha256(root / 'new-speech16k.wav'),
                    'asr_sha256': sha256(root / 'new-alignment.json'), 'asr_result': asr,
                    'human_confirmed_whole_utterance': True, 'voice_regeneration_allowed': False,
                    'scope': 'exact_voice_only_not_video_or_general_asr'}
        return root, text, approval

    def test_exact_human_approval_keeps_contradictory_asr(self):
        from production_diagnostic import check_human_approved_narration
        with tempfile.TemporaryDirectory() as td:
            root, text, approval = self.approved_fixture(Path(td))
            original = (root / 'new-alignment.json').read_bytes()
            result = check_human_approved_narration(root, text, approval)
            self.assertTrue(result['human_approved_exact_voice'])
            self.assertFalse(result['all_words_recognized'])
            self.assertTrue(result['first_and_last_word_retained'])
            self.assertEqual(result['asr_contradiction'], approval['asr_result'])
            self.assertEqual(original, (root / 'new-alignment.json').read_bytes())
            with self.assertRaises(Refused):
                check_human_approved_narration(root, text + ' autre', approval)
            approval['native_wav_sha256'] = '0' * 64
            with self.assertRaises(Refused):
                check_human_approved_narration(root, text, approval)

    def test_human_approval_cannot_allow_cut_or_shifted_samples(self):
        from production_diagnostic import check_human_approved_narration
        with tempfile.TemporaryDirectory() as td:
            root, text, approval = self.approved_fixture(Path(td))
            with wave.open(str(root / 'new-voice-4s.wav')) as stream:
                pcm = bytearray(stream.readframes(stream.getnframes()))
            pcm[3840 * 4:5000 * 4] = b'\0' * (1160 * 4)
            with wave.open(str(root / 'new-voice-4s.wav'), 'wb') as stream:
                stream.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
                stream.writeframes(pcm)
            approval['padded_wav_sha256'] = sha256(root / 'new-voice-4s.wav')
            with self.assertRaisesRegex(Refused, 'VOICE_SAMPLES_CHANGED'):
                check_human_approved_narration(root, text, approval)

    def test_authorized_code_resume_preserves_voice_call_and_rejects_worker_change(self):
        import copy
        from production_diagnostic import RESUME_LOCK, RESUME_LOCK_PATH, authorize_voice_resume
        with tempfile.TemporaryDirectory() as td:
            root, text, approval = self.approved_fixture(Path(td))
            base = RESUME_LOCK['base_configuration']
            state = RunState(root, base, max_gpu_seconds=2400)
            state.reserve('new4s/v3/1', 900)
            state.data['calls']['new4s/v3/1']['status'] = 'SAVED'
            state.complete('diagnostic_voice', {'test': 1}, [root / 'new-voice-native.wav'])
            state.complete('diagnostic_audio', {'test': 2}, [root / 'new-voice-4s.wav'])
            approval['original_state_sha256'] = sha256(root / 'state.json')
            approval['original_configuration'] = state.data['configuration']
            changed = copy.deepcopy(base)
            changed['human_voice_approval_lock_sha256'] = sha256(RESUME_LOCK_PATH)
            changed['code']['production_workers.py'] = 'f' * 64
            with self.assertRaisesRegex(Refused, 'UNAUTHORIZED_RESUME_CODE_CHANGE'):
                authorize_voice_resume(root, changed, 2400, approval)
            changed = copy.deepcopy(base)
            changed['human_voice_approval_lock_sha256'] = sha256(RESUME_LOCK_PATH)
            changed['code']['production.py'] = 'f' * 64
            authorize_voice_resume(root, changed, 2400, approval)
            resumed = RunState(root, changed, max_gpu_seconds=2400)
            self.assertEqual(resumed.data['calls'], state.data['calls'])
            self.assertEqual(resumed.data['stages'], state.data['stages'])
            self.assertTrue((root / 'state-before-human-approval.json').exists())

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
