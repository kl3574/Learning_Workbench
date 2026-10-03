# CI sandbox package availability diagnosis and proposed recovery

Status: diagnosis and bounded local verification complete; source change proposed only. No system package was installed or removed, no application code/test expectation changed, no remote workflow dispatched, and no publication performed.

## Observed failure and exact inputs

The six original backend/integration/browser jobs in push run 36365995687 and pull_request run 36365997123 failed during APT installation with exit 100 and `E: Version '0.11.1-1ubuntu0.1' for 'bubblewrap' was not found`. Their product test commands did not run. The six original logs and upstream receipts are retained byte-for-byte in `ci-original/`; `original-ci-pins.json` records their hashes.

The actual push checkout was 715a14440bbdef67dab336cf2778da2369641d33, and the actual PR merge checkout was a2f819169e05ab78cdd946f5c222b0b79cfbd44a. The latter workflow was retrieved read-only through the repository contents API and authenticated against its actual Git blob 150f2f7a8cf739ee8119c245d637fe52d889b061. Its bytes exactly equal the push checkout workflow. These were not assumed to be the PR head. All six original jobs report Ubuntu 26.04.1, runner image ubuntu-26.04 20260920.143.1 and provisioner 20260828.587. The exact official [image record](https://github.com/actions/runner-images/blob/ubuntu26/20260920.143/images/ubuntu/Ubuntu2604-Readme.md) is linked by the original logs.

The private investigation worktree is `m62-ci-sandbox-recovery-active`, branch `fix/M6.2-ci-sandbox-package-pin`, at the original push checkout. The sole product and engineering specification is PRODUCT_DESIGN.md 3.0.7, SHA256 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d. Relevant requirements are locked dependencies and actual evidence (§17, lines 792/812), privacy/isolation (§14), and authorized isolated numeric execution (line 515).

## Falsifiable hypotheses and results

| Hypothesis | Discriminating observation | Result |
| --- | --- | --- |
| The requested version is absent from the current distribution index | Independent official indices, empty dpkg status, exact old installation simulation | Confirmed: stage 01 exits 100 with the same missing-version error; policy lists 0.11.1-1 and 0.11.1-1ubuntu0.3 only |
| One of the other three exact pins is unavailable | Change only the bubblewrap version in the same empty-status simulation | Refuted for the captured indices: stage 02 exits 0 and resolves all four exact packages |
| PR and push run different sandbox-install instructions | Actual checkout workflow bytes and actual PR merge Git blob | Refuted for these six logs: the workflow bytes match |
| Signature/network/index acquisition failure caused the displayed error | Original successful index refresh and independent GPG/index chain | Not supported by these observations; independent signatures and complete package downloads pass |
| The product test suites failed | Inspect step boundary in six original logs | Not evaluated: those suites never started |

The primary failure mechanism is a stale exact APT package version in current indices. This says nothing about tests which were not reached.

## Actual APT and source authentication

APT used only private source/list/cache/log directories and an empty private dpkg status. Global APT parts and hooks were disabled. `apt-update.log` retains a harmless missing-directory warning caused by the disabled parts sentinel; this warning is not hidden. The initial update exited 0 but was started before the command recorder, so no pre-run timestamp/input receipt is claimed for that first command.

Stages 01–07 have actual command, UTC times, complete log hash, exit status, and before/after hashes for all 11,020 tracked files. `git-input-binding.json` independently proves that every before/after byte set equals its actual Git blob at 715a144. Twelve directly relevant original sources are copied with exact blob pins in `source-before/` and `source-before-pins.json`. No stage was rerun to obtain a preferred result.

Three InRelease signatures were independently accepted by `gpgv` with the installed Ubuntu archive keyring; the keyring hash and signing output are retained. Main Packages and the security Sources index match SHA256 and size in those signed releases. Four binaries and all four bubblewrap source distribution files match their indexed SHA256 and size. The current security release is dated 2026-09-28 01:15:29 UTC. These are [Ubuntu archive](https://archive.ubuntu.com/ubuntu/) files, not third-party mirrors or unsigned manual replacements.

The authenticated bubblewrap 0.11.1-1ubuntu0.3 amd64 package SHA256 is d3a6c1b6b0e0474eaed6dbd055c0d601fd875af153976a0dc4aae75f4ea10868. The extracted executable and installed `/usr/bin/bwrap` both hash to 523da3e7399044be5163aee6f57a77a6bef7454376e28f0a0627920bae1b76b6 and have mode 0755, not setuid. The installed AppArmor parser/profile and libapparmor/libseccomp bytes also equal their authenticated packages. `apparmor_restrict_unprivileged_userns` remains 1. The package extraction is private and does not run package maintainer scripts.

Private helper scripts were written before execution and their content hashes were recorded by their receipts; those helper hash readbacks occur at the end of execution. They are not misrepresented as part of the repository pre-run Git manifest. The two shared-library byte readbacks were taken during the focused test run; the earlier executable/profile binding precedes it.

## Security qualification and current product boundary

[Ubuntu USN-8779-2](https://ubuntu.com/security/notices/USN-8779-2), published 2026-09-18, says 0.3 reverses the 0.2 CVE-2026-87766 fix because of a Flatpak compatibility regression. [Ubuntu's CVE record](https://ubuntu.com/security/CVE-2026-87766) still labels Resolute vulnerable. The authenticated 0.3 source patch series contains CVE-2026-41163 plus a Debian diagnostic change; it does not contain the reverted symlink patch. The authenticated changelog identifies the addition in 0.2 and reversal in 0.3. The original 0.1 baseline therefore also lacked that later fix.

The [upstream advisory](https://github.com/containers/bubblewrap/security/advisories/GHSA-pxhw-h44j-8pfx) explains that the vulnerable setup operation follows attacker-controlled parent symlinks while creating filesystem paths, before the guest executes. Its fix is upstream 0.12.0. Availability or successful isolation tests do not prove that this third-party vulnerability has been repaired.

Static application review found the current document path uses an initially empty sandbox root, trusted runtime/package directories, and sealed uploaded bytes only at fixed `/input.bin` and other fixed destinations (`document_sandbox.py` lines 109–165, 199–224, 331–355). Uploaded filenames and archive directory trees are not used as mount destinations. The numeric path reads and seals the trusted closure with O_NOFOLLOW, validates logical library basenames, and mounts fixed logical files (`authoring_numeric_runtime.py` lines 80–106, 203–320, 432–456). Its user job contains no filesystem path selector. Neither product port binds an attacker-supplied directory tree as the sandbox root.

Inference: the setup precondition described by the advisory is not exposed by the reviewed current application input ports, assuming the installed application/runtime files remain trusted. This is a bounded applicability assessment, not a CVE fix, generalized immunity claim, or audit of other uses of the system bubblewrap binary. Future untrusted directory mounts or user-controlled destinations require a fresh assessment; tracking the official complete fix remains necessary.

## Actual local runtime checks

| Stage | Actual result | Log SHA256 |
| --- | --- | --- |
| 01 old exact package pins | exit 100, expected missing-version RED | 6b3079d26ab32dd74ca7747eb38f4a9a4987a22c37425b6a26821b519879e235 |
| 02 only .1 to .3 in install simulation | exit 0, exact four-package resolution | 3a3de46ad1628af3d31400aff4d83af211eb2fd55351f18082af36f9038965bd |
| 03 package policy | exit 0, private installed state empty | 60f99798711872ece01febb1840b0af2959a5b0c007706616a146596417b8070 |
| 04 authenticated archive/source | exit 0, signatures and hash chain pass | 832d9c4f19b73f496c2fee657e93e74663b482357db45393cee3b67bbf825c0d |
| 05 installed executable/profile binding | exit 0, exact authenticated bytes | 4d2e48597c5d4ed39c6641328d46204f5229026b4dc90f4316a503683b53b287 |
| 06 unchanged existing document runtime probe | exit 0, actual synthetic runtime PASS | ca30af6fc5b2c06967dd700e1cdbac4ebf600b53c9a721f8078e50a87a561456 |
| 07 unchanged three existing test files | 70 PASS, 1 SKIP, 5.67s | e586ac8e7f3de1246ede251ab43da2610f0735a8607f0d09dfe1a4037424b872 |

Stage 07 covers actual filesystem/network/process restrictions, resource limits, death propagation, PDF/DOCX extraction, and numeric runtime manifests. The one skipped actual-calculator case retains the pre-existing exact sealed-launch AppArmor loopback denial and BLOCKED verdict. Its arithmetic did not execute. No expected result, skip, timeout, retry, or isolation configuration was changed by this investigation.

These tests used the existing local Python 3.12.13 environment and authenticated locally installed package bytes. They do not replace a fresh GitHub runner execution or a complete backend/integration/browser run. APT simulations are dependency resolution, not a real fresh installation.

## Concrete proposal and next task

`PROPOSED.patch` is reviewable but not applied. It updates exactly three workflow occurrences from bubblewrap=0.11.1-1ubuntu0.1 to bubblewrap=0.11.1-1ubuntu0.3 and records this evidence/security qualification in ADR 0007. The other three exact package pins, runner label, namespace flags, capability dropping, AppArmor configuration, resource restrictions, and all test expectations stay byte-identical. No database/API/DTO migration is involved.

The coordinator must review this proposed runtime selection and its known CVE qualification before source application. If accepted, apply in this dedicated branch, validate the exact diff and publication scope, bind final source bytes, and hand off for coordinated CI publication. Actual remote backend/integration/browser outcomes must then be read back for the new push and PR merge checkouts. If a complete CVE fix is required before selecting this package, keep installation recovery pending and evaluate a separately pinned, reviewed compatible distribution/runtime; do not silently unpin, choose an unsigned build, disable isolation, or adjust fixtures to pass.

Original failures remain retained. This work does not close M6.2, authorize external model calls, prove model quality, or claim a release.

## Retrieval limitations retained

The four official pages were also requested as private raw snapshots. Both Ubuntu pages were captured with hashes. A direct upstream GitHub HTML request timed out, and a direct raw runner README request disconnected; their failure receipts remain in `official-pages/receipts.json`. Both pages had already been read successfully using the web tool, but no complete local raw snapshot is claimed for those two failures. The archive authentication chain and six original runner logs are independent of these optional page snapshots.
