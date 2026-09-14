# M3.1 practice hook lifecycle review

The permanent test is `apps/web/src/features/practice/usePracticeSession.test.tsx`. Its final run passed 6/6 cases in 2.69 seconds, and frontend `tsc --noEmit` passed. This package contains development review evidence, not an exact-commit full gate or native browser acceptance.

The harness executes the production React hooks and DraftStore over fake-indexeddb transaction behavior. HTTP replies, acknowledgements, and CAS errors are controlled synthetic transport responses. No listening HTTP service, browser engine, SQLite session, or actual private solution is involved. `PRIVATE_A_REVEAL_ONLY` is a synthetic test canary.

| Case | Result | Boundary |
| --- | --- | --- |
| Same hook instance changes A to B before automatic save | PASS | Defensive hook reuse; A is not rebound or written to B |
| Same hook instance changes identity with PUT in flight | PASS | Defensive hook reuse; B loads and late A acknowledgement cannot restore A |
| HTTP-shaped 412 response | PASS | Separate local/remote comparison; actual draft transaction preserves local candidate |
| Remote submitted while local response is unsent | PASS | Explicit keep-local preserves candidate and sends no response PUT |
| Unmount A with PUT pending, mount/write B, return to A | PASS | Production-lifecycle-shaped unmount/remount and explicit durable recovery |
| Unmount during A reveal, visit B, return to A | PASS | Late private canary stays out of B; A assistance reload does not preload private text |

Production `Shell.tsx` keys `PracticeView` by `active.id`; `model.ts` includes the session instance in the tab identity. Normal session/tab switching therefore unmounts the old hook. The first two tests intentionally cover the broader reusable-hook interface. The last two reproduce the relevant unmount/remount shape, without claiming that the full Shell or native UI is executed here.

## Retained history

- `review-receipt.json` and `initial.log`: 2 failures and 2 passes while the session-hook source changed. `source_stable=false` is preserved. Those results are not a current-source or immutable-SHA failure claim, and their same-hook rerender path is distinct from production keyed switching.
- The initial submitted control retained `results=null` after changing status; it was not a valid submitted DTO. This qualification is explicit in the public receipt. Its observed pass is only diagnostic history.
- `fixed-review-receipt.json` and `fixed.log`: the later six-case temporary harness used a complete strict submitted projection. The three imported practice modules and production key sources remained stable; an unimported `PracticeView.tsx` changed during integration, so no whole-UI stability claim is made.
- `fixed-initial.log`: an earlier six-pass temporary run before the submitted fixture correction; retained only as history, not used for final acceptance.
- `permanent-initial-typecheck.log`: the new test initially failed TypeScript because the core question model exposes optional `max_score`. The test now applies that model's default (`?? 1`); production code was not changed. The initial permanent runtime six cases already passed.
- `permanent-run.json`: final six-pass permanent test and successful frontend typecheck, with before/after hashes of the three practice modules, permanent test, Shell, and tab identity module. All six measured files stayed unchanged.
- `golden-verification.json`: Node evaluated the actual inline JavaScript strings. Strict Python `practice_fixture('hookreview')` comparisons verified all five public questions, their metadata hashes, and all three exact target references, including the TeX escapes. No private solution was serialized.

## Replay and publication

With the repository's locked dependencies and Node 24.21.0, run:

```sh
npm --prefix apps/web run test -- src/features/practice/usePracticeSession.test.tsx
npm --prefix apps/web run typecheck
```

Temporary historical harness snapshots are audit material: `<WORKTREE>` and `<HOOK_REVIEW>` replace local paths and must be supplied deliberately if replaying those snapshots. The permanent repository test needs no temporary fixture directory.

`manifest.json` lists raw and published SHA-256 values for every payload. Raw files remain unchanged outside the public repository. Public derivation replaces temporary checkout/review roots, any private home prefix, and the initial synthetic workspace nonce with documented placeholders. Receipts distinguish raw artifact hashes from published hashes. Every payload and this manifest passed `scripts.check_publication.py:inspect`; that bounded scan supplements this provenance review.

Cleanup completed: hooks unmounted and the fake-indexeddb store closed. No listening server was started. This task changed only the new permanent test and this evidence directory; it did not stage files, commit, or modify production hooks.
