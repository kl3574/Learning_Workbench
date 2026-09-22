Independently verified three bounded fixes: outer Shell safety controls under unknown/independent Policy; old-workspace rejection journal result suppression; primitive close-state notification without parent render feedback.

Actual independent rerun: 4 PASS / 3 modules in 1.16s, declared source before/after identical. The two original cache test files remain byte-identical to their RED versions. The current permanent Host test was imported unchanged; its original C red31/green32 pair had identical test bytes, while the current version carries a declared type-only annotation.

Original fix-only Shell OOM is retained as an actual failed run, not a fixture classification. No production edits, backend or native execution by this reviewer. No remaining blocker in the demonstrated mechanisms; this is not a general full-frontend acceptance.
