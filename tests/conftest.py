import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="ugcv2-test-")
os.environ["STUDIO_DATA_DIR"] = _TMP
os.environ["STUDIO_MODAL_ENABLED"] = "0"
os.environ["STUDIO_ALLOW_MOCK"] = "1"

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _boot():
    from backend.app import db, jobs
    db.init()
    jobs.start()
    yield


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    return TestClient(app)


def wait_job(client, job_id: str, timeout: float = 240.0):
    import time
    t0 = time.time()
    while time.time() - t0 < timeout:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed", "cancelled"):
            return job
        time.sleep(0.5)
    raise TimeoutError(f"job {job_id} non terminé")
