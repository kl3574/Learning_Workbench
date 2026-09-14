# M3.4 direct-grid overflow regression repair

This is focused development evidence, not complete exact-source acceptance. Parent retains the exact 63e4786 full run (65 passed, two failed). This package concerns only the DOCX width failure. The other practice bootstrap failure and its helper repair belong to a separate investigation. No grading, parser, role guard, import result or private-source policy was changed here.

## Diagnosis

The initial instrumented original DOCX case passed, but captured root scrollWidth 406 immediately after resizing to 390px and while focusing the candidate selector. The import dialog itself stayed at x14, width362, right376; its workflow stayed scrollWidth/clientWidth 360/360. After the actual React resize callback, root width became 390 before Tab completed. Thus the initial passing replay was not treated as a fix or as proof that the exact failure was random.

A controlled replay delayed delivery of real registered resize listeners. It preserved real upload, parser/worker, role transitions, source download, safe learner preview and original focus→Tab→root-width assertion. That assertion failed with root width406. During the same held callback interval, temporary CSS ablation measured:

| Temporary rule | Root width | App scroll width | Meaning |
|---|---:|---:|---|
| Current 63 CSS | 406 | 392 | Columns are zero, but old desktop panels and splitters remain rendered. |
| Hide splitters only | 406 | 390 | Does not remove root overflow. |
| Hide desktop panes only | 390 | 392 | Removes root overflow, leaving splitter border overflow inside the app. |
| Hide panes and splitters | 390 | 390 | Both bounds are correct. |
| Restore pre-63 column sizing | 390 | 680 | Root overflow absent, but central content width returns to zero; reverting would reintroduce the earlier defect. |

Removing each temporary override restored 406. These live same-page controls establish a regression mechanism introduced by the zero-column rule: it omitted synchronous hiding of desktop side children. They do not reconstruct unrecorded event timing in the original exact failure. The earlier 47e02d9 paragraph failure and its causal limits remain separately documented.

The minimal repair adds direct-child `.workbench-grid>.nav-pane`, `.workbench-grid>.agent-pane` and `.workbench-grid>.splitter` display:none within the existing max819 media query. Drawer contents are outside that grid and do not match. Original column sizing and pane behavior above819 are unchanged.

## Actual checks

- Instrumented original DOCX case: 1 passed, 5.8s; transient 406 captured.
- Controlled real-listener delay on 63 CSS: 1 failed at the original root-width assertion.
- Same controlled schedule with only the proposed CSS override: 1 passed, 6.0s; original workflow-width check and actual import confirmation also completed.
- Extended responsive test on a temporary exact63 source copy: 1 failed at the new grid-width check. Its root-width check passed in that assessment context; this distinction is preserved.
- Extended responsive test on repaired active source: 1 passed, 5.8s. Existing paragraph-visibility checks remain and two root/grid-width checks now run before releasing the actual resize callbacks.
- Original DOCX case on repaired active source: 1 passed, 5.9s, with the original test source, assertions and timeouts unchanged. This last run used the separately repaired shared bootstrap helper; its provenance is parent/backend owned.
- Existing frontend lint: exit0. Parent-configured targeted strict native typecheck: exit0 with its official Playwright declaration binding. These are not a full native typechecking or acceptance gate.

All actual commands and exits are recorded in `source/final-freeze.json`. The first responsive RED ran a temporary source copy with absolute imports bound to exact63; the active GREEN ran the repository file. They contain the same two added assertions but are not claimed byte-identical whole files because module paths differ. Two owned source hashes are stable across the final checks: style58eee0dc… and responsive test26b3e902…. The old DOCX source remained byte-identical. The shared bootstrap helper is not included in this agent's owned-file freeze.

## Visual and publication boundaries

All three PNGs were opened in the image viewer. They show real synthetic DOCX text, the provenance section, native focused previous-candidate button, and the dialog title/close button retained at390px. Before and after screenshots look similar because the defect affects the inert outer page bounds; the geometric width ledger, not an invented visible scrollbar difference, establishes the repair. Screenshots are unchanged bytes and normal390×844 viewports.

Public geometry selects every non-RAF, non-MutationObserver event; the complete raw ledger remains privately preserved. It records computed boxes/widths and element labels, not full DOM text. The original error-context public extract contains only its first Error details fence; the original full Page snapshot and Test source are excluded. The selected temporary DOCX probe is published with its shared helpers and complete selected case, excluding unexecuted document cases.

Logs normalize personal paths and process IDs. Manifest entries preserve raw/public hashes and each transformation. Temporary commands use isolated real data and ports, with launcher capabilities kept only in process memory; no profile, database, cookie, authorization value or bootstrap secret is included. The original-case final check used fixed5173/8765 only after the other agent released them; `ss` showed both unbound after its servers stopped. Final complete gates and CI are parent-owned and separate.
