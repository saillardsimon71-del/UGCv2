import sys

import pytest

from scripts.benchmark_ltx_minimal import main


def test_benchmark_refuses_compute_before_loading_any_worker(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", [
        "benchmark_ltx_minimal", "--source", str(tmp_path / "absent.mp4"),
        "--output-dir", str(tmp_path / "output"), "--workspace", "test-workspace",
        "--execute", "--confirm-spend", "non",
    ])
    with pytest.raises(SystemExit) as stopped:
        main()
    assert stopped.value.code == 2
    assert "autorisation humaine" in capsys.readouterr().err
    assert not (tmp_path / "output").exists()
