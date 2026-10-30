# UGCv2 autonomous production implementation plan

> Execution: inline, directly authorized by the user's mission. Continue PR #7.

Goal: connect the existing frozen catalog, planner and studio to a resumable CLI
and GitHub workflow, preserving approved media and refusing unqualified output.
Architecture: extend productions/UGCV2-FROZEN-RECIPE-20261030, not a second studio.
Stack: Python 3.11, FFmpeg, Modal 1.6.1, existing frozen LTX/TBDub/Chatterbox workers.
Spec: user mission in this chat, 2026-10-30.

Constraints: private media only in authenticated Modal storage; no engine edits,
no deployments, no secret replacements, no long GPU test, no automatic merge.
Only the existing four-second image-continuation recipe is eligible.

Review focus: interrupted GPU calls must not duplicate billing; source audio must
not be cropped to a fixed window; changed input must invalidate caches; unknown
scene layouts must not expose the original actor; technical validity must never
be promoted to human-quality approval.

- [ ] State and budget: atomic checkpoints, verified outputs, attempt reservation,
  private Modal persistence; tests for corruption, changed inputs, crash and limits.
- [ ] Import and narration: URL validation, download limits, pinned CPU ASR and
  EN-to-FR translation, existing V3 voice adapter, complete-word alignment and
  duration mapping; tests for invalid URLs, speech loss and timing expansion.
- [ ] Presenter and scene gates: exact frozen worker interfaces, native end-frame
  continuation, before/after retention, fail-closed quality policy and precise
  diagnostics; tests for missing qualification, recipe drift and pending calls.
- [ ] Assembly and rhythm: reuse planner.py and studio.py; paired sample/frame
  silence cuts with transcript protection; test real synthetic renders and sound.
- [ ] CLI/workflow: persisted run identifiers, resume and bounded segment retries,
  private results and public metadata-only report; integration tests with fake
  expensive adapters, then real CPU tests on GitHub.
- [ ] One representative private reference execution on GitHub using the actual
  approved takes, title, PiP and source speech; inspect/decode the delivered MP4,
  update PR #7, and report remaining qualification blockers without claiming
  arbitrary new-video production is proven.
