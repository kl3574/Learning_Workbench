# Published 1ad328d CI terminal evidence

Both runs concluded FAILURE. Push run 36981521690 actually checked out 1ad328d0d30c67030d7b62c5d712a37e9161a6aa; pull-request run 36981528047 checked out merge a92c0b8f8695033899e8670ab5c152ff72e2ed94. Every job and all original log lines are retained, with only the exact runner-home prefix transformed as listed in manifest.json.

| Gate | Push | Pull request |
| --- | --- | --- |
| Backend | PASS: 731 tests, 2 warnings; Ruff/mypy | PASS: 731 tests, 2 warnings; Ruff/mypy |
| Integration | PASS gate: 1747 tests, 1 numeric environment SKIP, 2 warnings | PASS gate: 1747 tests, 1 numeric environment SKIP, 2 warnings |
| Frontend | PASS: 562 tests /94 files, lint/types/build | PASS: 562 tests /94 files, lint/types/build |
| Security publication | PASS: 13811 tracked files | PASS: 13811 tracked files |
| Spec contracts | FAIL: 608 passed, 1 failed, 2 warnings | FAIL: 608 passed, 1 failed, 2 warnings |
| Native browser | FAIL: 107 passed, 1 failed | PASS: 108 passed |

The spec failure is the exact route projection assertion: the published head has 100 runtime endpoints and 126 declared endpoints, so 26 remain unimplemented rather than the assertion's 20. The six approved v3.0.9 endpoints were still local work. A later implementation must register them and regenerate contracts before accepting this gate; this failure is not retrospectively changed.

The browser failure is tutor.spec.ts:195, waiting five seconds for the real loopback Tutor run's completed heading. The same test passed in PR CI. Cause remains under investigation; the retained diagnostic is an observation, not proof of a fix. The failure artifact archive download SHA matches the uploader SHA; textual diagnostics are included and the original archive/screenshot retained privately. Fixture diagnostics also occur in this archive and must not be confused with the single failing test.

The numeric environment skip is not isolated numeric success. No real DeepSeek call, production InputProof, teaching or mathematical correctness acceptance, release, deployment, merge or issue closure is claimed. These results do not accept later local backend or UI changes.
