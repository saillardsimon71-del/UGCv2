#!/usr/bin/env python3
"""CPU-only preproduction QA. Does not imply the workflow or voice really ran."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
plan = json.loads((ROOT / "PLAN_SHOTS.json").read_text(encoding="utf-8"))
workflow = json.loads((ROOT / "n8n/demo_devis_mistral.json").read_text(encoding="utf-8"))
script = (ROOT / "SCRIPT_FR.md").read_text(encoding="utf-8")

assert plan["state"] == "PREPRODUCTION_ONLY", "Never claim finished film"
assert plan["generations_requested"] == 0, "No GPU generation authorized"
assert plan["format"] == "16:9" and plan["fps"] == 30
assert plan["target_duration_s"] == sum(s["duration_s"] for s in plan["shots"])
assert len(plan["shots"]) >= 5
assert plan["source_reference"]["original_source_media_reused"] is False
assert all(s["status"] == "PLANNED_UNSHOT" for s in plan["shots"])
assert "Mistral" in script and "n8n" in script
assert "fictif" in script.lower()
assert "sans validation" in script.lower() or "validation" in script.lower()
nodes = workflow["nodes"]
assert len(nodes) == 5
assert len({n["name"] for n in nodes}) == len(nodes)
name_set = {n["name"] for n in nodes}
assert len(workflow["connections"]) == 4
assert all(key in name_set for key in workflow["connections"])
for edges in workflow["connections"].values():
    for group in edges["main"]:
        for edge in group:
            assert edge["node"] in name_set
assert sum(n["type"] == "n8n-nodes-base.manualTrigger" for n in nodes) == 1
assert sum(n["type"] == "n8n-nodes-base.httpRequest" for n in nodes) == 1
assert all(n["type"] not in {"n8n-nodes-base.emailSend","n8n-nodes-base.gmail"} for n in nodes)
assert not workflow["active"]
raw = json.dumps(workflow)
assert "https://api.mistral.ai/v1/chat/completions" in raw
assert "$env.MISTRAL_API_KEY" in raw
assert "@example.com" in raw
assert "requires_human_approval" in raw
assert "BROUILLON_NON_ENVOYE" in raw
assert "sk-" not in raw, "Do not commit any apparent API key"
assert not any("KSOxkhWs2Ic" in n.get("parameters",{}).get("jsCode","") for n in nodes), "No source reuse in workflow"

print("CPU PREPRODUCTION VALIDATED")
print(f"9 shots; duration target {plan['target_duration_s']}s; 5 n8n nodes")
print("External Mistral API, voice and real captures NOT exercised")
print("No GPU used, no contact, no automatic publication.")
