# Static P2 closure: 196b6a9a

Fixed comparison: 28c92bdad181fdc0e297c05507f01234d26a86ac...196b6a9a7da9be94a12eaf5d93f63fb6eb041edc. The producer confirmed the target tree clean; a read-only status/HEAD check agreed. Only two changed files were reviewed, with necessary unchanged capability/spec context.

## Standards

No new finding. The production delta is one paragraph; it does not change permissions, capability requests, bootstrap or download behavior. The two added parameterized cases exercise the previously contradictory unknown and authorized observations rather than only checking a string in the initial state.

## Spec

The original P2 is closed at the static implementation level. CodexCapabilitiesPanel.tsx:64 now says that the local requirements document does not call Codex. It no longer declares the Broker disconnected regardless of the current unknown or authorized observation at :53/:56. This keeps the fallback statement consistent with v3.0.14 §6.6 (:350-354), §12.5 (:658), and independently observed account authorization (:1467). CodexCapabilitiesPanel.test.tsx:82-91 separately waits for the unknown or confirmed observation and rejects the old contradictory phrase. All product capability flags and permission logic are unchanged.

The original 28c OPEN finding is retained without modification in its original package (report SHA256 448a15a47c31aa57ae7b202ccacb7b1e1a6346c2e604dbadbeeb8afd49f95ba3); the earlier d973 report was also hash-checked unchanged. This closure does not claim an executed regression or full fallback/M6.3 acceptance.

This is a static review, not application or test execution. No application, DB, browser, network, CLI/model, system probe or previously rejected diagnosis was run. Product sources were not changed. One reviewer applied separate Standards and Spec axes; the earlier subagent attempt reached the thread limit, so this does not claim two independent reviewers. Reported producer/root test outcomes are not credited to this reviewer. The sole v3.0.14 PRODUCT_DESIGN.md remains SHA256 bed7c924955512ec4a6775812c80e6c5ce82e968f19feb403e568099f8dc4144. Earlier DCF complete-gate failures and unexplained setup errors are not reclassified here.
