# M6.3 independent Spec / HTTP / UI review

**No new confirmed Spec/HTTP/UI blocker. Overall acceptance remains held for the separate security review's P1 IPC and P2 FIFO findings.** Reviewed fixed backend1ab169a8, test-only8d34b044 and UI/native54fc2667 (UI90f35366/native7aacbd42). Independent combination6a594a58fd99b0eb2baafe845959e9f2886f60f9 changes only the two 8d test files relative to54fc. No product source was edited. Sole v3.0.13 SHA256949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05.

## Spec / HTTP

AppendixA PRODUCT_DESIGN.md:2193 requires the strict control shape and server-only paths; §12.5:653–659 separates observation from actual Broker session/tool duties. codex_dto.py:8–35, codex_http.py:12–25 and codex_capabilities.py:19–37 implement strict shape/empty request, current-session/workspace independent guard and a post-probe recheck. Production codex_probe.py:65–93 discards account/path details and fixes all three product flags false; upstream account/schema claims do not grant tools.

**10 new private HTTP/service probes PASS** in14.04s. Actual learner/author and open_book controls return200 with the same metadata under PRAGMA query_only; active independent returns409 before probe. Late revoke/expiry returns401; late independent returns409 without returning the probe value or adding post-transition DB writes. A forged workspace identity is401; unknown timeout stays503 without authorized=false. Table dumps remain exact outside explicit test-owner transitions. These are synthetic controlled probes, not CLI executions.

The earlier author/open_book expectation was withdrawn after checking §1.1:67, §20.2:984–997, §20.5:1023 and A2193: none requires this pure control GET to be author-only. Authoring generation's stricter §20.8 rule cannot be transferred to it. The UI is deliberately narrower. No role escalation finding is claimed.

## UI

CodexCapabilitiesPanel.tsx:12–43 binds workspace/access/admission/port and operation lifetime, reads fresh session before GET and discards late results. :49–64 keeps unknown separate, displays no raw error/account/path and explicitly marks generation/export/import-back unavailable. Parent AuthoringPanel.tsx:53 retains academic/ready admission. **Six new private UI probes PASS**: five invalidations during session await issue no capability GET; old-port completion cannot replace a newer observation. Strict TypeScript PASS. No new UI blocker found.

Separate backend Standards/security review owns the confirmed IPC/FIFO defects; this result does not clear them. Private-probe Ruff initially failed on one semicolon; original executed bytes/log remain, newline-only formatting passed Ruff without recounting behavior tests. Initial setup/audit harness errors are preserved separately.

All four test/check stages bind1321 complete non-progress Git inputs plus both private probes/runner, unchanged before/after. UI evidence independently rechecks32raw/33candidates, four1320-input stage bindings, actual native JSON and exact prefix transforms; producer's27focused/one native are not this reviewer's executions. Local native200 observations do not prove fence security. Evidence receipt includes the producer's additive SECURITY_LIMITATION hash.
