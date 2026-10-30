# New four-second diagnostic

Continue PR #7 and its production CLI, state and frozen workers. No replay of
the 6.52s reference. User authorizes one new private diagnostic generation.

- [ ] Add a private diagnostic profile and explicit diagnostic-only retrieval.
- [ ] Pin an unused clause from the authorized source, then translate on CPU.
- [ ] Produce one V3 utterance with the reference built-in voice and fixed settings.
  Preserve every sample; refuse duration overflow rather than retime/crop speech.
- [ ] Continue the retained native master, call LTX once and TBDub once, keep hashes.
- [ ] Run CPU tests, dispatch once from GitHub, fetch the private unvalidated MP4.

No model/recipe changes, no automatic approval/publication, no 20/60s render,
no retries with new seeds. On failure preserve intermediates and stop.
