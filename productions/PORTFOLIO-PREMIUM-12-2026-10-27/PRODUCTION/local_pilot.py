import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("--film", required=True, choices=["03-skincare-sensoriel", "05-architectural-living", "02-golden-reveal", "12-accessory-icon", "07-probleme-solution", "08-product-energy"])
args = parser.parse_args()
receipt = ROOT / args.film / "REPORTS/LOCAL_JOB.json"
status = {"film": args.film, "status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
          "purpose": "Persistent local fallback after GitHub CPU setup failure; existing Modal deployment only"}
receipt.write_text(json.dumps(status, indent=2), encoding="utf-8")
try:
    for shot in ("01", "02", "03"):
        subprocess.run([sys.executable, str(ROOT / "PRODUCTION/run_campaign.py"), "render", "--film", args.film,
                        "--shot", shot, "--confirm-spend", "oui"], check=True)
    subprocess.run([sys.executable, str(ROOT / "PRODUCTION/run_campaign.py"), "assemble", "--film", args.film], check=True)
    status["status"] = "real_mp4_created_pending_review"
except BaseException as error:
    status.update(status="stopped_on_error", error=str(error))
    raise
finally:
    status["finished_at"] = datetime.now(timezone.utc).isoformat()
    receipt.write_text(json.dumps(status, indent=2), encoding="utf-8")
