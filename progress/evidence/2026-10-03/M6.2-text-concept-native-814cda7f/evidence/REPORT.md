# Actual native concept-bound text editing

Fixed source **814cda7f73e864af7a499c0486b4fe9bc46fccb9**, clean isolated tree `m62-text-concept-native-oct03`. Chain: base 7a6a8a2a → backend 617fb004 → UI 86f96b5a (entire tree identical to the author's 91efdf09) → one new native testcase at 814cda7f. The sole PRODUCT_DESIGN v3.0.13 SHA256 remains `949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05`. No root tree, existing frozen tree, shared E2E helper, DTO, canonical spec or remote changed.

## Actual result

**1 native test PASS, 14.6 seconds**, one worker, zero retries, normal 5-second assertion timeout. The new test's 150-second total cap matches the existing dependency-edit vertical test; no global/default timeout was increased. It used actual Chrome, HTTP/SQLite/IndexedDB, fresh synthetic learnpack Import, Reader, title/body-only Draft create/PATCH, fresh Review and explicit synthetic human decisions, original four-field publication, explicit original-command replay and a real API restart with the same private database and browser profile.

Two ordered original concepts and two ordered exact block dependencies were retained. After draft freeze, fixture-only Content-owned publication advanced both concepts and both dependency blocks to current r2. Actual HTTP current reads verified r2, but the edited block's r2 metadata kept the original concept IDs and dependency refs in exact original order. A separate read-only Content-owned witness read before/after publication proved all original concept pins remain r1, including the concept below a dependency. The only witness change was the edited root ref becoming its new r2. Old r1 body and parent lesson's original r1 pin stayed unchanged. Candidate identity stayed unchanged in published GET; original publication ACK and replay ACK matched; original POST body matched explicit replay body. After closing Chrome and genuinely restarting API, the exact draft projection and complete witness matched and database inode/device identity was unchanged. No browser page errors occurred.

`text-concepts-actual.json` records only synthetic refs, witnesses, candidate, request and output facts. It excludes request/response headers, tokens, session responses, bootstrap values, raw environment, DB files and browser profiles. A non-secret synthetic actor_session_id is visible in the UI screenshot, as specified by §20.10.1; it is not an authentication credential.

At 1440 and 390 pixels, actual editor scrollWidth checks passed. Both screenshots were manually viewed: displayed hashes and dependency JSON wrap within the available width. These screenshots show the publication basis; the concept read-only display was verified earlier by native DOM assertions and is not claimed to appear in these later scrolled screenshots.

The native testcase and imported helper graph also passed strict TypeScript/no-unused using the installed Playwright's actual declaration exports. **1321 complete Git-tracked non-progress inputs plus four private config/typecheck/capture inputs** were hashed before and after; every tracked byte matched this fixed commit and before/after receipts are identical. Exclusions are progress/ and ignored tool/runtime artifacts, not selected production files. The source remained clean.

## Preserved failure sequence

- `native-red.log`: initial harness FAIL before Import because a Python list of Concept models was not converted to JSON-mode dictionaries. Its original testcase is retained; no production conclusion is drawn.
- `native-red-02.log`: corrected real-browser product RED on backend 617 with old UI. Import/Reader succeeded but the old nonempty-concepts guard made the editing region unavailable. Its exact testcase, screenshot and error context are preserved. The RED inventory is explicitly a post-run Git-byte receipt, not a claimed before/after capture.
- `native-typecheck-01.log`: initial harness declaration-resolution failure for the explicit installed Playwright index.mjs import. Private aliasing now re-exports the actual installed declarations without any/weakening strict checks. Later logs record PASS.
- Fixed GREEN also caches response bodies before closing their browser context. Consequently the archived native RED testcase and final testcase differ beyond the UI guard fix; this package does not claim a byte-identical native RED/GREEN. The UI author's separate final 12-probe RED/GREEN pair is byte-identical.

No failure original was overwritten or relabeled. A short private TMPDIR avoided known browser Unix socket path-length limits; no Chrome launch failure occurred in this new native sequence.

## Separate evidence scopes

| Source | Actual execution | Boundary |
|---|---|---|
| Backend 617fb004, author | 280 PASS; changed Python Ruff; mypy 236 sources | Includes 16 new HTTP and 12 V1/V2 oracle checks; not a full platform gate. 1318 complete non-progress tracked inputs. |
| Backend 617fb004, independent reviewer | 53 PASS, 73.23s; three production files Ruff PASS | 16 new + 12 oracle + 20 dependency regressions + five private HTTP cases; not additive to the author's 280. |
| UI 91efdf09, UI author | 77 focused PASS across nine files; strict PASS | 12 new probes included; 16030 inputs include historical progress evidence. No native execution by that agent. |
| Native combination 814cda7f, this package | 1 native PASS; native strict PASS | Actual synthetic software flow as described above; 1321 non-progress inputs. |
| Root's older 7a full native | Separate root report | Not coverage of this new slice; not counted here. |

Backend author report: `m62-text-concept-retention-evidence-oct03/REPORT.md`, SHA256 `7fca854d62f3b65632ff7e6e6a570489ee6e0f269770306f63de6d82c61cda89`. UI report: `m62-text-concepts-ui-evidence-oct03/REPORT.md`, SHA256 `22ce3707745932b6bd6b86f685d554818545f7d8c939e39392496e11fb9fc519`. Independent backend report: `m62-text-concept-independent-evidence-oct03/REVIEW.md`, SHA256 `c30121133dc0b9d9e92c927692dd9766ff7b6399392f9a05e8a3726b4a3b155c`. `UI-INDEPENDENT-REVIEW.md` is this author's separate bounded static review of the other agent's two UI production changes.

The original 12 actual V2 capture files and 16 original V1 oracle artifacts retain original bytes. Compatibility tests parse, canonicalize, hash and render ACK bytes across versions; they do not reopen the capture database in new code. Fresh HTTP/native tests separately prove real owner replay. The older capture's 16013 tracked inputs include progress and are not relabeled as the 1318/1321 non-progress scope.

Integrity begins at the draft freeze: arbitrary self-consistent pin substitution before freeze is outside this slice's guarantee. Base/descendant damage invalidates dependent candidate paths; damage only to the new published root blocks published GET/publication ACK while original candidate create/PATCH/Review facts retain their own bindings. This matrix is exercised by the separately bound backend tests, not simulated by this positive native case. Synthetic human choices establish software intent only, not mathematical, source-rights or teaching approval. This pure text flow runs no physical numeric execution or external model. Full combined Web/Python/native gates and any remote publication for this new slice remain outside this package.
