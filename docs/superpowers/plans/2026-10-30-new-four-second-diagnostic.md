# New four-second diagnostic

Continue PR #7 and its production CLI, state and frozen workers. No replay of
the 6.52s reference. User authorizes one new private diagnostic generation.

- [x] Add a private diagnostic profile and explicit diagnostic-only retrieval.
- [x] Pin an unused clause from the authorized source, then translate on CPU.
- [x] Produce one V3 utterance with the reference built-in voice and fixed settings.
  Preserve every sample; refuse duration overflow rather than retime/crop speech.
- [ ] Continue the retained native master, call LTX once and TBDub once, keep hashes.
- [ ] Run CPU tests, dispatch once from GitHub, fetch the private unvalidated MP4.

No model/recipe changes, no automatic approval/publication, no 20/60s render,
no retries with new seeds. On failure preserve intermediates and stop.

One dispatch executed: 41048730461 at commit 2fef188. The new V3 audio exists,
but its ASR did not confirm the expected complete text. NARRATION_TEXT_MISMATCH
stopped the pipeline before LTX/TBDub. No further model calls or reruns.
See DIAGNOSTIC_4S_RESULT.json. All available intermediate files were retrieved
privately, their completed-stage hashes checked, and an inventory created.
The remaining two steps are not achieved; no presenter MP4 is claimed.
