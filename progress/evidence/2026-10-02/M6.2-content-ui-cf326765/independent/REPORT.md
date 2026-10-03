# Content impact form recovery independent review

Fixed source: `50d960fec1a0dc5644f75f8b16e3c7252d1a4791`; review base: `e0e24592879ee60b437a6d7d5ff25632a58efae5`.

Outcome: PASS for the bounded form recovery and submit-race slice. No remaining blocking finding was identified in the reviewed changes. This is not a whole-M6.2 acceptance or an independent rerun of every author gate.

## Standards

Read the sole specification and the changed production seams, controlled form state, hook, Shell close paths, and tests. The new memory belongs to the page and original session, without adding durable actor inheritance or changing Content command ownership. The correction at 50d removes the unconditional form deletion; the existing exact-body consumption remains responsible for clearing only the submitted form. No original command body/key, CAS, or receipt check was weakened. Reviewed all nine changed paths against the fixed Git objects; the independent worktree remained clean.

## Specification and counterexample

The original e0 UI lost an unsent reason when Policy or role changes unmounted the form. Commit 3be retained the original form and basis in isolated page memory, hid them while current authorization was unavailable, and required fresh Session, event and target reads before restoring access. Changed target/current state retains the old basis and prevents submission. Explicit closing remains subject to the other unsafe editor/Review/command state aggregate; only explicit discard clears the temporary form.

A separate P1 remained in 3be: submit awaited the command-store load while the textarea remained editable. A newer Unicode/newline reason entered during that await was removed after the original command was durably stored, because releaseForm unconditionally followed the exact-match consumption. The real Panel probe failed on 3be and its original bytes are retained in the sibling red-evidence directory. The identical probe, SHA-256 `ccfe9db864b8e223e77a62f781ba3c88dd3aa451312ba1da040f395541d74f9f`, passes on 50d. Original body submission and newer form retention are both asserted.

## Independent verification

- Four focused files: 42 tests PASS. Includes the unchanged race probe, Policy/role and foreign-session isolation, fresh basis, command replay/CAS, explicit discard, and other unsafe-state aggregation.
- Two native scenarios: PASS in 1.1 minutes. Actual SQLite, HTTP and IndexedDB cover the existing Content impact command flow and unsent form retention across repeated role cycles, fresh reads, changed target basis, return/close behavior and explicit discard. No Provider calls.
- Source binding: all nine changed paths equal fixed commit bytes; reviewed worktree clean after execution. Author manifest: all 47 entries verified against their private originals. See SOURCE_BINDING.json for exact hashes.

The author's 116 focused tests, 660 full Web tests, lint/build and two native scenarios are author evidence, not additional independent executions. No independent full Web, static or build rerun is claimed. The earlier original form-loss RED, the 3be submit-race RED, and all author harness failures remain preserved; later PASS results do not erase them.

## Evidence boundary

`focused-01.log` and `native-01.log` are original independent outputs. `native-data/` and `native-artifacts/` are private runtime evidence. SOURCE_BINDING.json binds source and gate logs. This report is private and performs no GitHub or main-worktree mutation. The native port window has been released.
