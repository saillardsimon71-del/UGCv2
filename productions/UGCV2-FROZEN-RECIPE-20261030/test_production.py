import tempfile
import unittest
from pathlib import Path

from studio import Refused


class StateTests(unittest.TestCase):
    def test_lock_file_can_survive_process_without_blocking_resume(self):
        from production_state import RunLock
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'production.lock'
            with RunLock(path):
                with self.assertRaisesRegex(Refused, 'RUN_LOCKED'):
                    with RunLock(path):
                        pass
            self.assertTrue(path.exists())
            with RunLock(path):
                pass

    def test_stale_remote_final_cannot_be_fetched_after_failure(self):
        import json
        from production import fetch_deliverable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'final.mp4').write_bytes(b'bad-candidate')
            (root / 'report.json').write_text(json.dumps({'status': 'BLOCKED_NO_DELIVERABLE'}))
            with self.assertRaisesRegex(Refused, 'NO_DELIVERABLE'):
                fetch_deliverable(root, root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_resume_verifies_files_and_inputs(self):
        from production_state import RunState
        with tempfile.TemporaryDirectory() as td:
            state = RunState(Path(td), {'url': 'one'}, max_gpu_seconds=30)
            output = Path(td) / 'take.bin'
            output.write_bytes(b'approved')
            state.complete('take', {'audio': 'a'}, [output])
            self.assertTrue(state.cached('take', {'audio': 'a'}))
            with self.assertRaisesRegex(Refused, 'inputs changed'):
                state.cached('take', {'audio': 'b'})
            output.write_bytes(b'corrupt')
            with self.assertRaisesRegex(Refused, 'checksum'):
                state.cached('take', {'audio': 'a'})

    def test_reservation_survives_crash_and_blocks_duplicate(self):
        from production_state import RunState
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = RunState(root, {'url': 'one'}, max_gpu_seconds=30)
            state.reserve('take/ltx/1', 20)
            resumed = RunState(root, {'url': 'one'}, max_gpu_seconds=30)
            with self.assertRaisesRegex(Refused, 'already reserved'):
                resumed.reserve('take/ltx/1', 20)
            with self.assertRaisesRegex(Refused, 'budget'):
                resumed.reserve('other', 20)
            with self.assertRaisesRegex(Refused, 'configuration changed'):
                RunState(root, {'url': 'two'}, max_gpu_seconds=30)


class ImportTests(unittest.TestCase):
    def test_only_youtube_video_urls(self):
        from production_input import youtube_id
        self.assertEqual(youtube_id('https://youtu.be/KSOxkhWs2Ic?t=49'), 'KSOxkhWs2Ic')
        self.assertEqual(youtube_id('https://www.youtube.com/watch?v=KSOxkhWs2Ic'), 'KSOxkhWs2Ic')
        for url in ['file:///secret', 'https://youtube.com.attacker/watch?v=KSOxkhWs2Ic',
                    'https://youtube.com/playlist?list=abc', 'https://user@youtube.com/watch?v=KSOxkhWs2Ic']:
            with self.subTest(url=url), self.assertRaises(Refused):
                youtube_id(url)


class NarrationTests(unittest.TestCase):
    def test_complete_transcript_including_edges(self):
        from production_narration import verify_transcript
        words = [{'text': 'Bonjour', 'start_s': .1, 'end_s': .4},
                 {'text': 'tout', 'start_s': .5, 'end_s': .8},
                 {'text': 'le', 'start_s': .9, 'end_s': 1.0},
                 {'text': 'monde', 'start_s': 1.1, 'end_s': 1.5}]
        verify_transcript('Bonjour tout le monde.', words, 1.7)
        for text in ['tout le monde', 'Bonjour tout le', 'Bonjour autre le monde']:
            with self.assertRaises(Refused):
                verify_transcript(text, words, 1.7)

    def test_timeline_expands_instead_of_clipping_voice(self):
        from production_narration import duration_map
        result = duration_map([{'start_s': 0, 'end_s': 2, 'audio_duration_s': 3.1},
                               {'start_s': 2, 'end_s': 4, 'audio_duration_s': 1.1}], 4)
        self.assertGreater(result[0]['output_end_s'], 3.1)
        self.assertGreater(result[-1]['output_end_s'], 5)
        self.assertEqual(result[0]['audio_speed'], 1)


class QualityTests(unittest.TestCase):
    def test_unknown_quality_is_blocking(self):
        from production_quality import require_qualified_generation
        with self.assertRaisesRegex(Refused, 'LIPSYNC_VALIDATOR_UNQUALIFIED'):
            require_qualified_generation()


class RhythmTests(unittest.TestCase):
    def test_cut_rejects_words_and_audible_samples(self):
        import subprocess
        import wave
        from production_rhythm import trim_silences
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, audio = root / 'source.mp4', root / 'audio.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=red:s=160x90:r=25:d=2', '-f', 'lavfi', '-i',
                            'sine=frequency=440:sample_rate=48000:duration=2',
                            '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(source)], check=True)
            with wave.open(str(audio), 'wb') as stream:
                stream.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
                stream.writeframes(b'\0\0' * 96000)
            words = [{'text': 'Bonjour', 'start_s': .8, 'end_s': 1.2}]
            with self.assertRaisesRegex(Refused, 'INTERSECTS_WORD'):
                trim_silences(source, audio, words, root / 'out.mp4', [(20, 30)])
            report = trim_silences(source, audio, words, root / 'out.mp4', [(5, 15)])
            self.assertEqual(report['output_frames'], 40)


class ContinuationTests(unittest.TestCase):
    def test_native_frame_mapping_and_frozen_recipe(self):
        from production_workers import frozen_recipe, continuation_anchor
        from unittest.mock import patch
        self.assertEqual(frozen_recipe()['ltx_seed'], 2026103017)
        with patch('production_workers.command') as cmd:
            continuation_anchor('before.mp4', 100, 'anchor.png')
            self.assertIn('select=eq(n\\,95)', cmd.call_args.args[0])

    def test_saved_call_without_id_never_resubmits(self):
        from production_state import RunState
        from production_workers import model_call
        from unittest.mock import Mock, patch
        with tempfile.TemporaryDirectory() as td:
            state = RunState(Path(td), {}, max_gpu_seconds=30)
            state.reserve('take', 20)
            function = Mock()
            with patch('modal.Workspace.from_context') as workspace:
                workspace.return_value.hydrate.return_value.name = 'lucj76861'
                with self.assertRaisesRegex(Refused, 'REMOTE_CALL_UNCERTAIN'):
                    model_call(state, 'take', Mock(), function, (), 20)
            function.spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
