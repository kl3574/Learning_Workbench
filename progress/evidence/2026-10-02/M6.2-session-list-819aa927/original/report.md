# Approved session/editor continuity implementation

Only Draft editor create/PATCH command continuity changes. SessionResponse actor_session_id is the actual authenticated persisted SessionIdentity.id; no actor claim is accepted in write DTOs. Existing Review, publication, Learning and authoring journals retain their original page/access/session restrictions.

New editor commands use a strict version 2 journal containing workspace_id, actor_session_id, exact route, original key, full body/CAS and immutable original baseline before HTTP. Recovery performs a fresh strict Session GET; cross-page/access recovery also checks exact original draft material or original Content metadata/body. Only explicit user replay sends HTTP. Original ACK remains separate from current draft GET. Original v1 records are neither migrated nor supplemented with the current actor. Permission failure/unknown state clears protected projections while existing unsaved-memory guards retain necessary memory. Material-read errors never become mutation rejection receipts.

## Evidence

- session-red: 2 failures before Session implementation; session-green-01: 35 passed.
- journal-red: 1 failed, 7 passed before v2 support; journal-green: 8 passed.
- focused-web-01: 99 passed. full-web-final: 578 passed, 95 files.
- backend-02: 118 passed, actual SQLite/HTTP Session, Edit commands, current role and independent/open-book Policy, forged actor input, no-store and zero-write GET.
- native-final: 1 actual Chromium/HTTP/SQLite/IndexedDB flow passed: create ACK lost then page reload with original replay; unexecuted original CAS after competing HTTP update returns 412; patch ACK lost then page reload, browser closure and actual API restart with original replay. One draft, revisions 1..4 exactly, four successful original commands bound to the actual actor. Current draft and old Content pin checked independently. Same-workspace new bootstrap cannot replay old command; legacy v1 remains byte-identical/read-only. Actual IDB transaction abort and role roundtrip preserve protected memory.
- mypy-final-02: 227 files passed. ruff-final-02, web-lint-final, build-final, generate-check-final and staged-publication-final passed.
- Generated contracts: 106 actual operations, 127 declarations, 54 core models. Spec SHA35018183fbd6d7253001e71b2c932eb10410813ed81625936a667a6be71d0c29. No list handler is invented; root implements that separate approved route.
- Frozen 98-path manifest: after-manifest-v2.json SHA e9a80d42385aad818259d62796379a33e06a65de555f93bf64a3ad22b9d4832e. The earlier 97-path freeze is preserved separately; the added path only corrects the explicit route coverage count.

## Preserved failures and boundaries

- generate-01: approved new collection route lacked M6.2 catalog ownership. Exact owner mapping added.
- generate-02: normative Session row repeated the separately declared role route. Root supplied approved mechanical spec correction d47f147; duplicate detection retained.
- native-01: harness attempted a new UI command while another original command was unknown. The existing guard correctly blocked it. Harness now uses an actual competing HTTP client to advance the server head; native-02 and native-final pass without weakening the guard or extending timeouts.
- ruff-01: test imports appended after functions; moved to module top.
- mypy-final: incorrect manually combined module roots duplicated canonical.py. Project-standard no-argument mypy passed.
- contracts-session-final: 610 passed, 1 failed because old assertion expected 20 undeclared runtime gaps. Approved v11 has 127 declarations against 106 actual operations, so exact assertion is 21. Full rerun receipt is retained separately.
- Starlette deprecation and existing Vite chunk-size warnings retained. No real provider, secret-store access, remote mutation, progress/spec edits in implementation commit or real academic quality approval.
- This isolated base does not include later independently approved CodeMirror and Edit publication UI combination. No whole M6.2 acceptance is claimed. Full Python suite is not run in this slice; full contract and scoped backend checks are the stated boundary.

Final implementation commit: 2340a1c7c73faee218c2fc5736cf880a8ee73274. Final contracts-session-final-02: **611 passed**. Fixed tree is clean; all 98 frozen files match.
