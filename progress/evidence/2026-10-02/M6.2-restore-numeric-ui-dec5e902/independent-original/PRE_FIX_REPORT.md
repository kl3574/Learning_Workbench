# Independent Restore numeric UI review — original fixed source

Scope: root UI `2e90c235` (13 files), integrated fixed `8acdd2e4051dd22b513fcf79f2c8684ea37b2d78`; sole PRODUCT_DESIGN v3.0.12 SHA `1c571ee91a7d39dedd2e8395f48766bd6183d496154ee9bdd9b67cb978ff26d7`. Original source is unchanged. Only private review probes are untracked. The subsequent backend ea3 and native extension 7023 are not part of this original execution result.

## Standards

Separate subagent static review found no demonstrated engineering-boundary or reportable maintainability defect. It read all 13 changed files plus journal, memory and safe Jobs dependencies. No functional test claim follows from that static result.

## Spec

**P2: CRLF original-body selections use normalized textarea offsets against unnormalized source.** `RestoreNumericMaterialEditor.tsx:18` passes real `selectionStart/End` directly to `selectedSourceSpan` (`restoreNumericForm.ts:33-37`). HTML textareas expose LF-normalized text; their UTF-16 offset after a CRLF is one shorter than in the original body. With `🧮 原文 é\r\nGiven x=2...`, selecting actual displayed `2` then explicitly applying it to the variable location produces `{start:"16",end:"17",quote:"="}` instead of `{start:"17",end:"18",quote:"2"}`. Every preceding CRLF adds another error. The exact-location requirement at spec line 1253 prohibits source newline normalization. The later schema/owner checks refuse the wrong numeric quote, so this is a functional source-location failure, not publication bypass or execution authority escalation. Fix by mapping displayed selection offsets back into original source, retaining original quote/codepoint boundaries; do not rewrite body bytes. Author/root notified and owns repair.

Exact three-case independent DOM probe SHA `2424152fdf4934f295b1e2f2c8d724af5c03dfca25f80faadd248cc5fa0850df`: LF and lone CR pass; CRLF fails. `selection-01` records 2 PASS / 1 FAIL and 1221 unchanged input hashes. Original probe copied into evidence. Command: `bash scripts/node.sh npm --prefix apps/web test -- src/features/contentRestore/independentNumericSelectionReview.test.tsx`.

Other independently tested boundaries:
- First IDB abort retains raw `2e0`, `3.0`, `-0`, combining Unicode and CRLF reason across unmount/recovery, without POST.
- Delayed fresh permission read after re-lock cannot reveal original form or begin source GET.
- Actual access-generation mutation discards a late preview ACK; original journal remains byte-equivalent and numeric replay cannot inherit the newer access generation.
- Previous page/actor unknown preview cannot be replayed or replaced with a new key; no expansion of Edit-only v3.0.10.
- Other workspace/new actor cannot recover original raw form or ACK memory.
- Binding created by another operation while form is isolated preserves the old form but disables preview.
- Actual useAuthoring hook: cancel busy prevents close; lost ACK remains durable and dirty/beforeunload-protected even with academic Policy paused.
- Real DOM separate approval: rejected approve removes old approval panel; explicit current read then explicit decline sends one new key; no automatic retry.

## Actual evidence and limits

`focused-02`: 16 files / 177 PASS (156 existing Restore tests, 9 independent probes, 12 existing NumericCheckPanel/useAuthoring dependency tests), 2.05 s; 1220 inputs unchanged. `lint-fixed`: PASS; original tracked source unchanged. `probes-01`: original independent nine probes PASS. `focused-final` retains a private-probe timing failure: it sampled parent dirty state immediately when cancel port was entered, before React effect delivery; safe=false and closeSafe=false already held. Only the probe was corrected to await the parent effect; v1 and v2 copies and exact v1 hash readback retained.

`native-02`: actual browser/HTTP/SQLite/IndexedDB/sealed runtime, original fixed `restore-numeric.spec.ts`, 1 PASS / 11.9 s; 1220 inputs unchanged. Manually entered plan; deliberately lost first preview ACK; original-key replay; exactly one independent execution decision. Actual started `2026-10-02T12:13:49.469612Z`, exit 1, verdict BLOCKED, outcome environment_unavailable. This proves the UI preserves actual environment failure, not numeric PASS, math correctness or publication. No page errors. Actual JSON and 1440/390 screenshots retained. `native-fixed` is a preserved harness failure before any test: external private config lacked package `type:module`; added only an evidence-directory package.json then reran unchanged product source. No default 5173/8765 webservers used; RestartRuntime random ports with private short TMPDIR.

No full Python/Web rerun performed in this review. Root full-gate claims remain separately attributed to root evidence. No Provider use, remote operation, spec/progress/backend/main edits. Original P2 remains open in this report; any repair rerun will receive a distinct source binding and addendum.
