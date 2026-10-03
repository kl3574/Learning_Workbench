# Group numeric decline diagnostic receipt

The original combined native gate remains FAIL (92 passed / 9 failed). Its
authoring-groups.spec.ts:235 case failed at source254: the 10-second response
waiter did not observe the exact decline decision response. The retained
original error context does not establish that no POST was sent. Root cause:
UNKNOWN. No product repair is claimed.

The authorized single targeted execution of the unchanged original case passed
(case12.7s, Playwright13.0s, wrapper13.326481820s), exit0. The probe records154
metadata events, zero omitted: one trusted decline pointerdown/up/click with an
enabled pending button in view, exact decision request18 / response200 / finish;
the separate later approval request25 / response202 / finish. The original test
checks the original ACK, independent stored decline readback and later numeric
execution, and these assertions remain unmodified. This later PASS is not an
explanation or closure of the original failure.

Four code-grounded hypotheses were kept falsifiable: (1) actionability/scroll
prevented click delivery; (2) ready/busy/pending-command guards rejected the
operation; (3) local persistence prevented dispatch; (4) request/response failed
at the network boundary. None explains a reproduced failure, because this run
did not reproduce it. The observed run progresses beyond every boundary;
historical alternatives remain unresolved. No fabricated focused RED or
speculative product change was added.

Scope: fixed1fffd996e9334f7f28dcdeb970430c9aa4052ee3, unchanged original test,
three diagnostic-only runtime lines importing a private metadata observer.
The private config omits the unrelated global web servers; the original test's
own AuthoringRuntime uses dynamic API/UI ports. Original120s case timeout,
10s actions/responses, 5s assertions and retry0 remain. The981 actual engineering
inputs were identical before/after execution, including the disclosed observer
entry points. Only those entry points were then restored byte-exact to HEAD;
the separate after-removal snapshot and clean status are recorded. No main tree
or fixed8765/5173 service was touched.

Two preceding harness errors are retained: ESM config-load exit1, then anchored
grep selection exit1 (No tests found). Both executed zero cases and are neither
product RED nor PASS. A corrected --list returned exactly the source235 case
before the sole execution. Original native190-member manifest was reverified
without modifying any member. Screenshots and local synthetic fixture evidence
are private; this package has not been published or publication-scanned.

Next: preserve UNKNOWN for this failure. Further diagnosis needs an observed
failure with the same bounded click/request/persistence boundary evidence under
the relevant scheduling conditions; do not infer a cause from this isolated
PASS, rerun the full suite for green, or relax deadlines. No further browser run
is performed in this task. Real provider, human content approval and release:
NOT_RUN.
