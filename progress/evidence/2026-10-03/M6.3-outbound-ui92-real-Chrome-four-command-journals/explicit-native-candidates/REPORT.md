# M6.3 outbound UI — fixed 92c8836c native run-01

The bounded native acceptance completed with exit 0 on 2026-10-04. It used actual Chrome, the app HTTP routes, SQLite, and IndexedDB in a separate fixed-source worktree. It does not establish actual Codex CLI, remote provider/model, host sandbox, academic quality, or overall M6.3 acceptance.

## Fixed execution

- Source: `92c8836c5729c0a7a128a3a128d9e62c997da657`.
- Worktree: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-codex-outbound-native-owner-oct04`.
- Private evidence: `<LOCAL_HOME>/.cache/learning-workbench-acceptance/m63-outbound-ui-native-92c8836c-oct04/run-01`.
- Wrapper: `run-01-launch.py`; native command and exact harness hashes are in `run-01/command.json`.
- Started: `2026-10-04T12:19:26.283244+00:00`.
- Finished: `2026-10-04T12:19:58.612066+00:00`.
- Elapsed: `32.32882374399924` seconds; native and wrapper exit codes: `0`.
- Chrome reported `154.0.8037.97`, with actual 1440 and 390 viewport checks.
- Full nonprogress Git input count: `1443`. Native and outer-wrapper manifests independently compare all records; both before/after files are byte-identical, every actual source blob matches fixed Git, and status is clean. No generated source output changed.
- Raw success log SHA-256: `805fdf31b8912fae193e5d22a9ed9a1fe1babda1c2040f020efb233d390c50dc`.
- The three harness files were privately reviewed by root before the explicit run-01 authorization. `PRE_RUN_BINDING.json` preserves the earlier NOT_RUN state and is not a current outcome record.

## Actual bounded checks

1. Production-default Codex proof/executor registration was empty. A real prepared turn reported unavailable, the UI preview was disabled, and an explicit actual preview POST returned HTTP 503 with `CODEX_INPUT_PROOF_UNAVAILABLE`. The synthetic model-request counter was zero at this checkpoint.
2. After explicitly injecting the trusted local fixture, preview, grant, revoke, and start each persisted the original actor, key, full command body, and read basis before POST. Each real acknowledgement was deliberately lost. A real refresh made zero automatic POSTs; explicit replay used the original key and full request body, returned a byte-identical complete acknowledgement, and persisted that full acknowledgement while preserving the original command. A further refresh preserved it. The four full-ack hashes and command/body/key hashes are in `receipt.json`.
3. Learner access used safe turn control to revoke while the subject consent GET was denied with 403. A later current revoked GET did not overwrite the original active grant acknowledgement.
4. Start returned the original queued 202 acknowledgement. During the one controlled response the actual browser role changed to learner. Subject result access was denied with 403. Owner finalization reported failed / `POLICY_DENIED` while retaining the complete original Unicode response. After restoring author access, UI text and exact UTF-8 response hash were verified. Explicit original start replay still returned the original queued acknowledgement, separately from the terminal failed current/result GET.
5. Actual open-book and independent assessment attempts hid subject UI and returned subject GET 409, while safe control allowed explicit revoke and later revoked no-op. These checks caused no second synthetic request.
6. A real API restart and persistent Chrome restart retained original commands, forms, bootstrap bytes, and the result. They generated zero automatic POSTs or second synthetic requests. There were three API process generations total.

The bootstrap runtime was an explicit controlled synthetic fixture called once. The default proof checkpoint counted zero model requests. The explicitly trusted phase counted exactly one in-memory synthetic transport request. Actual Codex CLI, external model/provider, and tools remained NOT_RUN.

The receipt's `actual_external_requests: 0` field is a harness isolation declaration, not a browser/OS-wide network meter. The supported claim is the observed synthetic counter plus the privately reviewed fixture containing no external model call. `safe_http_timings` records browser page request events only; it does not include the explicit `page.request` 503 probe. That probe's actual status and safe error were asserted in the fixed native source at line 99 and are reflected in the successful receipt, not retained as a raw response body. No global network audit is claimed.

## Six original screenshots

All six images were individually opened and inspected; all six measured dialog scroll widths equal client widths, and document widths equal their 1440/390 viewports. No horizontal overflow was observed. The images contain controlled synthetic content and public opaque identifiers, without an auth code, cookie, CSRF value, or secret material.

- `default-proof-blocked-1440.png`: preparation JSON and controlled input are visible; the long region's BLOCKED paragraph is outside this frame. This image alone is not visual proof of the full BLOCKED message.
- `default-proof-blocked-390.png`: runtime warning visibly includes `CODEX_INPUT_PROOF_UNAVAILABLE` and the explanation that approval/outbound start is unavailable. The top action area is outside this frame.
- `learner-safe-revoke-1440.png`: safe control JSON visibly records revoked consent; long region content pushes controls toward the lower edge.
- `learner-safe-revoke-390.png`: narrow safe-control JSON is visible, but the revoked status lies below the frame. This image alone is not visual proof of that status.
- `failed-turn-complete-response-1440.png`: visible complete output, terminal failed outcome, explicit non-completion explanation, original Unicode response, UTF-8 hash, and quality NOT_RUN boundary.
- `failed-turn-complete-response-390.png`: the same result boundary, answer, hash, and quality explanation visibly wrap within the narrow frame.

The original framing is retained. No screenshot was replaced or used to overstate the supported visual claim. Root's independent screenshot review remains separate.

## Explicit candidate policy

Only the exact files named by `publication-candidates/allowlist.json` are candidates for later review. They are not automatically published. Text candidates use only the exact `<LOCAL_HOME>` to `<LOCAL_HOME>` transformation; the manifest records raw and candidate hashes and replacement counts. PNG candidates are byte-identical originals. Complete source maps contain only public tracked relative filenames, Git/hash metadata, byte counts, and empty status; every record was checked against a closed schema and the two independent maps agree. The human review covered the candidate log, runner, command/readback, receipt fields, compact full safe HTTP timing list, screenshot contents, and metadata schema/path boundary.

The original three fixture/harness files remain available for root's private readback, but are deliberately not candidates: they include synthetic secret/setup operations. Private path inventory, fixture binding/proof files, database, browser profile, archives, request contents, key material, cache, and TMPDIR contents are excluded. Nothing outside the explicit candidate list is authorized by this report. Earlier 29e native evidence and all earlier UI RED/fixed evidence remain independent and unchanged.
