# Review local-input preservation during Publication reads

Fixed commit `3adcdec4f3184f97837c56240c30fc63e733909b`; clean isolated tree `$HOME/.cache/learning-workbench-acceptance/m62-review-form-input-fix-oct02`; base c2f47a2778bb6a78c73237f8bb89fb271dfedcd6. Historical sole spec v3.0.12 SHA1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7. No spec/progress/generated/backend/dependency/remote modifications. Exact five source files archived under fixed-source/ and matched to committed Git bytes in fixed-readback.json.

## Demonstrated problem and repair

New Review receipts trigger the independent Publication selection/session refresh. Its effect-reported busy state previously disabled Review textareas, even though Review's own access and operation were ready. In the observed native schedule the same textarea briefly enabled, received focus, then disabled and blurred to BODY. Playwright fill could pass actionability before that boundary and send Chromium Input.insertText after it, returning without a beforeinput/input event. It had never written the note into DOM or original actor form memory. Subsequent correct Policy recovery therefore showed the earlier confirmed blank form.

ReviewForms now accepts a separate submitBlocked flag. ReviewPanel uses its own busy/ready/pending-memory state for editing and also preserves the precise-current-basis restriction for restored forms. Publication safety remains a submit guard for current create, current human decision, and both recovered form branches. All other command, parent close, Policy, actor/session, unknown/ACK, and recovery boundaries remain unchanged. A Publication read cannot take focus from local Review input. This also preserves existing local edits during subordinate busy operations without authorizing a POST.

The original CI PR37007484342/job110839065970 remains a recorded failure. Its historical artifact lacks failure-time memory/input traces. This is a demonstrated matching mechanism and repaired product boundary, not proof of the CI event's unique cause. Already received input was retained in the observed positive control; no accepted-input deletion was demonstrated.

## Test-first evidence

| Stage | Fixed scope | Actual result |
|---|---|---|
| native-red-c2 | Permanent actual HTTP/SQLite/UI fixture, hold named Publication port's real session response; no fake session, backend writes, or artificial input | FAIL1: textarea disabled at unchanged5000ms editable assertion |
| panel-red-c2 | Permanent current/recovered form probes with actual Panel+Publication and a held read | FAIL2 at editable assertions |
| panel-green | Exact same permanent test bytes, two production file repair | PASS2 |
| native-green-original | Same permanent native plus original unmodified CI case | PASS2/36.7s |
| focused-recovery | Review/Publication/Edit/Restore/Import tests before updating obsolete expected-disable assertion | PASS271/FAIL1; retained verbatim |
| final-full-web | Final five-file source | PASS832 across118files/8.55s |
| final-native | Final source, original case19.4s + new held-read case16.7s | PASS2/36.4s |
| final-lint | TypeScript strict/noUnused | PASS |
| final-build | TypeScript + Vite | PASS/834modules; existing large-chunk warning retained |

The one focused failure was ReviewImportShell.test.tsx's old assertion that subordinate Publication busy disables the reason. It is updated to assert continued editing and exact new reason retention; all discard/close-disabled, release, and new-explicit-click assertions remain. Final full Web includes the complete affected272-test subset.

Both new permanent test files are byte-identical between old-c2 RED and repaired GREEN (red-regression-hashes.json; fixed-readback.json). The original review-form-memory.spec.ts and all its5000ms assertions are byte-identical to c2. Final four gates each freeze1240source inputs, unchanged during execution and all matched after commit to final source. App gates ran before commit using those same bytes; they are not represented as tests of a different Git snapshot.

The new native uses RestartRuntime's actual private SQLite/API/UI/worker, original synthetic assessment/package fixture, explicit Review creation, real subsequent Policy/role changes, original actor fresh recovery, and explicit close/discard. The gate delays only the named Publication.session response after real HTTP returned; it never fabricates data or authority. While held, note remains focused/editable, both otherwise-valid create/decision buttons remain disabled, and no decision is sent. After release buttons enable; subsequent recovery preserves exact notes/reasons and still requires explicit confirmation. No models or academic approval are exercised. New DOM tests also keep both current/recovered forms editable while submission and parent safety stay blocked, revoke Policy during the hold, reject late payload reappearance, and explicitly recover original text.

## Earlier diagnosis archive

Read-only c2 diagnosis is independently frozen at `$HOME/.cache/learning-workbench-acceptance/m62-review-form-race-audit-evidence-oct02/REPORT-checkpoint.md` (SHA3a6007d76ed4246104a11e4a0bcd1d652c729c6a0342818caa505a1e250c272c), with55-file manifest SHAeba87385fa40332faac23d339960c4eeee46943159387d82a0f12b6e76cc8360. It preserves original local PASS, lightweight actual Review GET hold FAIL before Policy, passive timeline PASS, deterministic transport-delayed final original5000ms failure, and private probe design/setup failures. The transport interception exists only in that private diagnostic; it is not in committed tests or production.

## Boundaries

No complete Python or entire native suite rerun was necessary for these two frontend modules; those are NOT_RUN for this commit. Parent will independently review/integrate the five-file commit, including any newer ReviewPanel Single-publication conflict. No default5173/8765 ports were occupied; all native gates used private config webServer:undefined and short private TMPDIR. Own npm ci completed with0reported vulnerabilities. No environmental secret enumeration, provider, or remote action.
