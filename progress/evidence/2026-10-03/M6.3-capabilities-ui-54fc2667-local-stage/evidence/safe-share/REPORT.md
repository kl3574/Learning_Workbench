# M6.3 scoped Codex capability UI: fixed local stage

Tested combination54fc266798a1e4be2142266012f24f468a57fb98 is UI90f35366 + native7aacbd42 + backend1ab169a8 cherry-pick, on published0ede. Only this source is covered. A final combination with newerM6.2e287 and contract-test correction8d34b044 is still pending; this is not wholeM6.3 completion or publication.

- 27 focused Web tests across five files PASS (includes23newclient/component cases and four existingAuthoring cases); strict TypeScript PASS.
- Native helper/test strict types PASS. One actual production API/browser/restart case PASS6.7s, one worker, zero retries. All1320 tracked nonprogress engineering inputs matched Git before/after everygate; actual runner and nativeconfigs are bound. FullWeb/Python/native suites were not run at this stage.
- Both actual GETs returned200, available=true, authorized=false, adaptercodex-cli/0.160.0, three productcapabilityflagsfalse. The source-boundtest exercised actual control-probe isolation without HTTP orCLI substitution. API restarted to a new process using the sameDB; secondexplicitread matched. AuthoringJobsunchanged; learnerrole disabledthecheckandhidpriorstatus.
- The public UI only starts reads after an explicit click and freshauthor/Policy/workspace admission. Scope/accessgeneration/port/unmount changes reject late observations. Unknownerrorsarekeptdistinctfromunavailable/unauthorized; rawaccount,error,andpathsarenotdisplayed. No automatic generation/login/thread/turn or artifact operation is provided.
- Root visually inspected actual1440/390screenshots: readableconnectionstateandcapabilitylabels, no horizontaloverflow. BothcapturedstatusobservationsbelongonlytothestableisolatedBroker, nottheuserglobalCLIsession.

The native test has explicit degraded branches for missing or unsupported environments; those branches would verify UI degradation only. This recorded local run took the real200/availabletrue branch twice. Physicalnumeric sandbox acceptance is separate and remainsBLOCKED; this control-probe isolation is not a numericfallback. PlatformDeepSeek/fullCodexworkflow andacademicacceptance remainNOT_RUN.

The earliercandidate.json correctlyrecords testsNOT_RUN at its originalcommitcheckpoint. Its rawreceiptisretained; thisreport recordslaterexecutions. gates.py ranonlyfocused/strict; gates-native.py withprivateconfigs rantheactualnative-types/nativecommands. No executedreceiptisrewritten. Backend1ab's separate broadcontract gate had731PASS1old-route-countFAIL; owner8dcorrects the testonly, pendingfinalcombinedgate. ThatfailureisnotrelabeledbytheseUIpasses.

Explicit SAFE_SHARE candidates permit only exact local-home prefixes in text; originalbytes/hashesremainprivateandunchanged. Imagescontainonlysyntheticworkspacecontentandwerevisuallyreviewed. No DB,cookie,header,profile,bootstrapvalue,globalconfigorunlistedrawpayloadisadmitted. No sourcepush, merge, release or deployment by this stage.
