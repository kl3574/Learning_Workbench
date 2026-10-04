# Fixed 28c static addendum

Reviewed `d973e71f45909722f26d477358aee4d5d7141056...28c92bdad181fdc0e297c05507f01234d26a86ac`: the added native case, its selector revision, and the capability footer/test. Producer explicitly confirmed final full SHA and clean tree before review. Only fixed Git objects and necessary fixed context were read; no subsequent WIP or unsealed diagnosis was inspected. Sole spec v3.0.14 SHA is unchanged. The sealed d973 review remains intact.

## Standards

0 confirmed findings in this increment. Native `local-task-document.spec.ts:49` still asserts the exact original multiline textarea value after returning from the close guard; `:60` requires the same exact accessible textbox identity to be absent after fresh learner permission. Changing both from exact label matching to exact textbox role does not weaken either expected value or revocation condition. Saving the already-validated synthetic bytes at `:37` preserves the artifact if later checks fail. No old test/shared helper/default timeout is changed. The native case names browser-page mutations separately from the explicit setup/role HTTP commands (`:29-41,52-68`); zero captured page writes must not be read as zero writes in the whole test.

## Spec

**P2 — unconditional disconnection claim (`CodexCapabilitiesPanel.tsx:64`).** With `admitted=true`, the new footer always says “仍未连接 Codex”. A 503 at the capability read yields the existing “当前状态未知” branch (`:39-41,53`) at the same time; a valid `available=true, authorized=true` response yields “连接与授权状态已确认” (`:56`) alongside that footer. The existing strict client permits the latter while all three product flags remain false (`codexClient.ts:15-18`). §6.6 (`PRODUCT_DESIGN.md:354`) labels the unavailable/unauthorized fallback, while §12.5 (`:658`) and §20.16 (`:1467`) keep authorization an independently observed fact. “This four-input document does not call Codex” is the narrow truthful statement; it should not overwrite unknown/confirmed Broker status. Add ordinary unit coverage for those two observations. This is a static render-path finding, not an executed counterexample.

The native case remains within the authorized four-input fallback: exact synthetic Markdown, omitted provider/ref values, one fresh Session GET during download, retained close guard, and fresh learner rejection. It does not claim controlled Codex generation, artifact import or academic approval. Actual browser behavior and the producer's label-diagnosis explanation were not independently reproduced here.

## Limits

One reviewer, separate Standards/Spec assessments; the previous thread-capacity limitation prevents claiming two independent agents. No tests, app, browser, CLI/model, DB, network, remote mutation or system/previously refused diagnostic was executed. Producer-reported native/Web/strict results are not credited as this review's execution.

Standards: 0 findings. Spec: 1 open P2 at fixed 28c.
