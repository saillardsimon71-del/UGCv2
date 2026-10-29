import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import run_production as runner


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'film'
        shutil.copytree(runner.ROOT, self.root)
        self.root_patch = patch.object(runner, 'ROOT', self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def test_missing_frame_prevents_remote_access(self):
        (self.root / 'ASSETS/shot-03-firstframe.png').unlink()
        with patch.object(runner, 'remote_preflight') as remote:
            with self.assertRaises((ValueError, FileNotFoundError)):
                runner.render('oui')
            remote.assert_not_called()

    def test_changed_frame_prevents_remote_access(self):
        with (self.root / 'ASSETS/shot-02-firstframe.png').open('ab') as output:
            output.write(b'changed')
        with patch.object(runner, 'remote_preflight') as remote:
            with self.assertRaises(ValueError):
                runner.render('oui')
            remote.assert_not_called()

    def test_rerun_prevents_remote_access(self):
        with patch.dict(os.environ, {'GITHUB_RUN_ATTEMPT': '2'}):
            with patch.object(runner, 'remote_preflight') as remote:
                with self.assertRaises(ValueError):
                    runner.render('oui')
                remote.assert_not_called()

    def test_prior_receipt_prevents_remote_access(self):
        (self.root / 'REPORTS').mkdir(exist_ok=True)
        (self.root / 'REPORTS/shot-01-receipt.json').write_text('{}')
        with patch.object(runner, 'remote_preflight') as remote:
            with self.assertRaises(ValueError):
                runner.render('oui')
            remote.assert_not_called()

    def test_wrong_workspace_stops_before_function_lookup(self):
        with patch('modal.Workspace.from_context') as workspace, patch('modal.Function.from_name') as function:
            workspace.return_value.hydrate.return_value.name = 'wrong-workspace'
            with self.assertRaises(ValueError):
                runner.remote_preflight(runner.check())
            function.assert_not_called()

    def test_missing_weights_stop_before_function_lookup(self):
        with patch('modal.Workspace.from_context') as workspace, patch('modal.Volume.from_name') as volume, patch('modal.Function.from_name') as function:
            workspace.return_value.hydrate.return_value.name = 'lucj76861'
            volume.return_value.hydrate.return_value.listdir.return_value = []
            with self.assertRaises(ValueError):
                runner.remote_preflight(runner.check())
            function.assert_not_called()

    def test_timeout_cancels_and_never_retries(self):
        function = Mock()
        function.get_current_stats.return_value = SimpleNamespace(num_running_inputs=0, backlog=0)
        call = function.spawn.return_value
        call.object_id = 'fc-CPU-TEST-ONLY'
        call.get.side_effect = TimeoutError('CPU TEST timeout')
        with patch.object(runner, 'remote_preflight', return_value=function):
            with self.assertRaises(TimeoutError):
                runner.render('oui')
        function.spawn.assert_called_once()
        call.cancel.assert_called_once_with(terminate_containers=True)
        with patch.object(runner, 'remote_preflight') as remote:
            with self.assertRaises(ValueError):
                runner.render('oui')
            remote.assert_not_called()

    def test_audio_has_exact_duration_and_no_clipping(self):
        import wave
        from array import array
        output = self.root / 'test.wav'
        runner.foley(output, [6.6, 10.9, 12.1, 13.3])
        with wave.open(str(output), 'rb') as source:
            self.assertEqual((source.getnchannels(), source.getframerate(), source.getnframes()), (2, 48000, 720000))
            pcm = array('h', source.readframes(source.getnframes()))
        self.assertGreater(max(pcm), 1000)
        self.assertLess(max(abs(value) for value in pcm), 32767)


if __name__ == '__main__':
    unittest.main()
