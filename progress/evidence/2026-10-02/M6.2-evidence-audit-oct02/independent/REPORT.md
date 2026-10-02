# Staged evidence publication audit, 2026-10-02

Verdict: PASS for the seven explicitly scoped staged evidence packages, after the two documentation findings below were corrected. This is a mechanical evidence/provenance/publication audit, not a new independent product review of the Session implementation I authored. No repository, index, remote, original evidence, or product source was changed by this audit.

The audit is pinned to `snapshot-02/` and `audit-02.json`, captured from Git index blobs at main HEAD `6b0dc4dccc7fe0159f9787ff9e79ed9f2192e46b`. Seven package inventories contain 280 files: 273 manifest entries and seven outer manifests. All 280 were staged. Each published hash, raw-source hash, exact transformation, and package inventory matched. The a5 shareable ZIP's 24 member bytes and ZIP hash matched, including the explicitly mapped `.txt` to `.log` rename. The added progress-sync package's three original bodies/readback files and scoped summary also matched; this audit did not independently query or mutate GitHub again.

A bounded scan of all 280 captured files found no credential, private-key, bootstrap-token, JWT, or personal absolute-home matches (including bare home prefixes without a final slash). This is pattern-based review, not a proof that arbitrary personal prose or every possible secret encoding is recognizable. Public files contain synthetic local test data; no private API key/provider call was used.

## Findings resolved before this verdict

1. Six outer transformation descriptions originally repeated a real bare personal-home prefix. This was both a disclosure in the explanatory text and a false negative in the existing scanner, whose pattern required a trailing slash. Root changed only the descriptions to `exact personal-home prefix replacement with $HOME only`; the mapped evidence bytes were unchanged. A separate scanner repair is authorized, but is outside this evidence verdict and must not change frozen gate inputs.
2. Eight impact-independent stdout rename notes said `bytes unchanged` despite the separately disclosed home-prefix transformation. Root clarified that `.log` is the filename extension change and content transformation is recorded separately. Raw/public hashes were always correct. `audit-01.json` retains the eight ambiguous-note findings; `audit-02.json` has zero issues.

## Original namespace and fixed-source checks

`bindings-01.json` records 72 actual command receipts whose log hashes match the retained raw logs; before/after hashes, counts and unchanged flags were also checked wherever receipts carry them. Five nested manifests verify 579 original private entries in their original namespaces (271 + 148 + 31 + 70 + 59). These nested manifests do not claim that all those originals, images, or large source manifests were publicly copied; the outer manifest controls the public inventory and rename mappings.

Fixed-source comparisons use content hashes against Git blobs, not a false assumption that a pre-commit receipt HEAD must already equal the later commit. All comparisons matched:

- Original actor: 98 frozen paths at `2340a1c7c73faee218c2fc5736cf880a8ee73274`.
- Combined actor: 99 frozen paths at `b78f781393dd4f266b2db73c26a366f4476d615c`; independent reviewer binding also matched all 13,970 tracked files at that commit.
- Restore original: 22 implementation files at `da867f4c253123934b4cabb1c8b7e53e7259e942`.
- Impact independent: all six fixed source hashes at `d636fe54d33ac53f0f5710a856db01dca7afd256`.
- Session/list final focused, Ruff, mypy, TypeScript and generated checks: each 1,156 before-manifest inputs matched `819aa927a58bc95ac45ac317b73dd2cb6938ee0e`.
- Restore root full-Web-fixed, lint-final, build-final and native-six: each 1,175 before-manifest inputs matched `6b0dc4dccc7fe0159f9787ff9e79ed9f2192e46b`.
- Interrupted initial full Python, missing-toolchain probe, exact-lockfile dependency installation: each 1,156 inputs matched `819aa927a58bc95ac45ac317b73dd2cb6938ee0e`.

## Result boundaries verified from original logs

- Actor original: 611 contracts/Session, 118 scoped backend, 99 focused Web, 578 full Web, native 1; combination: 114 HTTP/contracts, 129 focused Web, 618 full Web, native 4. These are different frozen inputs and are not credited to a5 remote CI.
- Session/list combination: 168 scoped Python PASS, static/generation PASS; runtime107/declared127 remains a partial endpoint implementation, not whole-M6.2 acceptance.
- Independent Session: 102 focused Web (including seven independent negatives), 114 HTTP/contracts, native2; no independent full-suite claim is invented.
- Impact independent: 115 related +18 DTO +15 probes =148 PASS. Root final related111 PASS. Original FK fixture failures, independent integrity failures and other harness/lint failures remain represented in the public logs.
- Restore combination: initial full Web660 PASS/1FAIL retained, unchanged focused2 PASS retained, revised isolated/durable-ACK assertion full Web661 PASS across104 files retained; native-six6 PASS; build/lint PASS. Unsupported worked-example numeric evidence remains unsupported, not silently accepted.
- a5: push36988843781 six jobs PASS/browser108 PASS; PR36988849056 five jobs PASS and Tutor browser107 PASS/1FAIL. Both integration jobs1890 PASS/1skip. All12 logs retained. Same Git tree between a5 and actual PR merge checkout does not turn the failed PR event into PASS, nor establish its unique cause.
- Initial819 full Python: interrupted exit2,6 FAIL/1403 PASS/1SKIP, all six failures missing TypeScript compiler. Explicit environment probe and exact-lockfile installation are retained. This is not a complete-suite failure count or a successful retry. At this audit, no terminal receipt was present for the replacement full-Python run.

The newer private full-native receipt appeared during the audit: exit0 at6b, with `unchanged:false` and generated docs/ui outputs. It is not among the seven packages audited here, and this report does not certify its changed-output restoration or promote it to a frozen unchanged gate. Root was notified for its separate handling. The published RUNNING statements are dated snapshots; the scoped six-native claim remains accurate. No synthetic human decision or mock provider result is claimed as real teaching-quality/provider validation.

## Reproduction

Private `audit.py` captures index bytes and verifies mappings/security patterns; `bindings.py` verifies original receipt and manifest hashes plus Git content bindings. `snapshot-02/` preserves the exact reviewed public bytes. `audit-01.json` preserves the corrected note finding. All original evidence remains in its existing private location. No live test was rerun or result manufactured by this audit.
