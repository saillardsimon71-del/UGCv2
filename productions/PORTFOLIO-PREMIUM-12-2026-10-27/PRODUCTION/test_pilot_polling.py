import base64
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import modal
import run_campaign as runner


class PollingTests(unittest.TestCase):
    def exercise(self, exception_type=None, deadline=False, prior_attempts=0):
        film = "03-skincare-sensoriel"
        source = runner.ROOT / film
        with tempfile.TemporaryDirectory(prefix="sqv-polling-unit-") as temp:
            root = Path(temp)
            folder = root / film
            for part in ("ASSETS", "PROMPTS", "RENDERS", "REPORTS"):
                (folder / part).mkdir(parents=True)
            (root / "PRODUCTION").mkdir()
            for name in ("INPUT_REVIEW.json", "BUDGET.json"):
                shutil.copy2(runner.ROOT / "PRODUCTION" / name, root / "PRODUCTION" / name)
            for name in ("PRODUCTION_PLAN.json", "PROMPTS/shot-01-payload.json", "ASSETS/shot-01-firstframe.png"):
                shutil.copy2(source / name, folder / name)
            if prior_attempts:
                (folder / "REPORTS/ATTEMPTS").mkdir()
                for index in range(prior_attempts):
                    (folder / "REPORTS/ATTEMPTS" / f"shot-01-attempt-{index}.json").write_text("{}")
                (folder / "REPORTS/MANUAL_TECHNICAL_RETRY.json").write_text(json.dumps({"shot": "01", "max_total_attempts": 2}))
            call = Mock(object_id="fc-unit-test-no-remote-call")
            result = {"video_base64": base64.b64encode(b"unit-test-bytes-not-a-film").decode(),
                      "metadata": {"continuity_mode": "image", "generation_seconds": 1}}
            call.get.side_effect = [exception_type(), result] if exception_type else [result]
            function = Mock()
            function.hydrate.return_value = function
            function.get_current_stats.return_value = types.SimpleNamespace(num_running_inputs=0, backlog=0)
            function.spawn.return_value = call
            workspace = Mock()
            workspace.hydrate.return_value = types.SimpleNamespace(name="lucj76861")
            fake_modal = types.SimpleNamespace(
                Workspace=types.SimpleNamespace(from_context=lambda: workspace),
                Function=types.SimpleNamespace(from_name=lambda *a, **kw: function),
                exception=modal.exception)
            info = {"streams": [{"codec_type": "video", "width": 768, "height": 1344}],
                    "format": {"duration": str(121/24), "tags": {}}}
            timer = Mock(side_effect=[0, 601]) if deadline else Mock(return_value=0)
            with patch.object(runner, "ROOT", root), patch.object(runner, "check"), patch.object(runner, "probe", return_value=info), \
                    patch.object(runner, "command"), patch.object(runner.time, "monotonic", timer), \
                    patch.dict(sys.modules, {"modal": fake_modal}), patch("builtins.print"):
                if prior_attempts >= 2:
                    with self.assertRaisesRegex(ValueError, "hors limite"):
                        runner.render(film, "01", "oui")
                    function.spawn.assert_not_called()
                elif deadline:
                    with self.assertRaises(TimeoutError):
                        runner.render(film, "01", "oui")
                    call.cancel.assert_called_once_with(terminate_containers=True)
                    call.get.assert_not_called()
                else:
                    runner.render(film, "01", "oui")
                    self.assertEqual(call.get.call_count, 2)
                    call.cancel.assert_not_called()
                    receipt = json.loads((folder / "REPORTS/shot-01-receipt.json").read_text(encoding="utf-8"))
                    self.assertEqual(receipt["status"], "technically_checked_visual_review_pending")

    def test_builtin_poll_timeout_keeps_the_same_call(self):
        self.exercise(TimeoutError)

    def test_modal_poll_timeout_keeps_the_same_call(self):
        self.exercise(modal.exception.TimeoutError)

    def test_real_deadline_cancels_once_and_stops(self):
        self.exercise(deadline=True)

    def test_third_attempt_is_rejected_before_remote_call(self):
        self.exercise(prior_attempts=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
