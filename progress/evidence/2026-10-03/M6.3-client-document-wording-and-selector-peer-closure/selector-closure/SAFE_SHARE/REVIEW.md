# Static selector delta: 06659cea

Fixed comparison: 83daf55c1d536ab018182fc2419f3424faaba1e2...06659cea9fdf7746f8758fba863ed167cb1974d6. The owner tree is fixed and clean. Only tests/e2e/local-task-document.spec.ts changes.

## Standards

No finding. The two selectors at :100 and :118 remain scoped to the Import dialog and retain exact accessible names; they now select a combobox role rather than an implicit label. UploadForm.tsx:24 and DraftPreview.tsx:70 are the corresponding labeled select controls. Values remain markdown and the exact selected draft ID. The extra line is explanatory commentary. Mechanical byte reconstruction confirms these are the only replacements: all other test code and assertions are identical, and both test cases remain.

## Spec

No finding or weakened requirement. The first case still checks exact four-input downloaded content, exclusions, GET/session-only download, close/dirty guard, current-role revocation and no second download. The second still explicitly chooses the actual downloaded bytes, requires staged/preview/source/artifact hashes and exact retained-original bytes, checks draft/user_supplied preview and disabled confirmation, empty course readback, and the exact page mutation list containing only POST imports. It does not add commit, publication or Codex operations. The scope remains ordinary staging under §6.1/:320, §20.3/:1008 and Appendix A/:1569-1571. Existing limits in the 83daf static report remain: authentication/role setup precedes mutation capture; empty courses is not a whole-database zero-write proof.

This reviewer executed only evidence hashing/scanning and exact text reconstruction, not either native case, application, DB, CLI/model, network or system probe. No product files or prior receipts changed. One reviewer applied both axes; no full fallback/M6.3 acceptance is claimed. Earlier test failures and producer run results are not reclassified or counted here.
