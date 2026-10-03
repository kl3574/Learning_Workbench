# Read-only outgoing publication audit

Published base: `a5c4ca9d46a740737d29499fb212cdfcd64187f8`. Final audited HEAD: `98eaf27de7b241de11b714a0e47cc54f120604b2` (the prior fixed source checkpoint was `dec5e9028b833aca3abc989ddc17cd25036f1dba`). This audit performed no main-tree mutation, history rewrite, commit, push or remote request. It read no environment or authentication source.

## Results

- PASS: all outgoing reachable Git objects relative to the published base: 43 commits, 545 trees and 1062 blobs. All1062 blobs are covered by1162 changed-path/blob pairs, including intermediate commit versions. Every pair was scanned at its real repository path. Commit/tree payloads were also content-scanned under metadata paths. All strict scanner findings: zero.
- The final progress/evidence commit contributes391 added/modified paths, all included in that history scan. The original303-file request estimate is not used as the final audit count.
- Separately, three post-commit worktree evidence files were scanned: zero findings. They and the final HEAD were stable during capture. Their paths/hashes are in WORKTREE_SCAN.json. This is a bounded snapshot, not a statement about later writes.
- Final index bytes were unchanged during audit: SHA-256 `e118d7dddfc67f6a7fdf74da65ecc908132fe8595dd79ed83361a33d531e0813`. Raw before/after index files, staged listings, status listings, complete outgoing object IDs and all path/blob checks are retained privately. This is a post-commit index binding, distinct from the root operator's earlier precommit index receipt.

The exact current strict scanner was compiled from the audited repository bytes without importing or writing cache files. SHA-256: `b42f875f7d0a41f78cd7a59b97948b59f1e6146c8ba9198e6c737e284a834d33`; it matched the audited HEAD blob. No scanner exclusions or rule changes were used. A scanner PASS is bounded to these rules and snapshots, not a proof that arbitrary private prose can always be detected.

## Three historical description matches

All three old blobs corrected by5d230f18 still trigger the strict scanner and are retained as findings in LEGACY_DESCRIPTION_FINDINGS.json. They are not automatically exempted. Each is exactly the blob already present in the published base tree, so none is a newly outgoing object.

1. `progress/evidence/2026-09-15/M5.2-3dd-ci/README.md` — old blob `a59e1a0209a1b58803f3180b800013de6d7968ed`: a standard hosted-runner home-prefix literal describing a redaction transformation. It is tooling provenance prose, not a user's private payload.
2. `progress/evidence/2026-09-15/M5.2-d65-recovery-gates/driver-independent-review/review.txt` — old blob `2784c28ab11a83556a7bff2e5be4cdc3094138f1`: slash-separated conceptual path-category words that match the home-path pattern; not an actual filesystem disclosure.
3. `progress/evidence/2026-09-15/M5.2-f9-backend-gates/independent-review-v1.json` — old blob `b4ffbd7a874355a140d98f754e460206551278a6`: the same conceptual category-enumeration issue; not an actual filesystem disclosure.

Each reason remains exactly `suspected credential or personal absolute path; inspect privately`. No matched literal, credential or original matching context is reproduced here. These three checks support a descriptive-origin classification for these specific files; they do not weaken the scanner or claim an exhaustive baseline-history audit. Existing published history is unchanged.

## Capture sequence and limits

The first fixed dec5 capture found zero outgoing findings across42 commits/715 blobs/771 path-blob pairs. During this task the operator staged and committed the evidence as98eaf27d. A worktree-only selector then naturally returned an empty set; that empty set is not used to certify the staged391 files. Instead the final audit rescanned the complete a5-to98 outgoing graph, covering every391-path addition/change explicitly. Earlier captures are retained privately, with their original index/status bindings.

This report does not authorize or perform publication, and does not attribute local tests to CI. The root operator owns the final publication decision and any later commit scan. No source directory from another project was scanned.
