# Evidence qualifications

wire-red-01 and wire-green-01 used the actual generated Web request client with a synthetic fetch boundary and fake-indexeddb DraftStore. The inherited runner boundary string incorrectly says actual local HTTP/owners. No live API owner or browser ran in those checks. Raw receipts and run.py remain unchanged; run-v2.py uses an accurate boundary.

Development invocation at 23:57:58 collected zero tests (three suite failures): ENOENT in a default /tmp Vitest transformation path, after a missed TMPDIR setting. This is an environmental collection failure and no product result. The original tool output is retained in the conversation. No complete before map or standalone raw log was captured for this invocation; no such evidence is claimed. Source was subsequently committed as f0566809 without changes before the next observed run.

wip-tests-02.log is the subsequent private TMPDIR development result: 2 FAIL / 16 PASS. Both failures concern jsdom Blob.arrayBuffer missing, before the intended post-download Policy check; not a demonstrated product failure. Test fixtures then use Node BinaryBlob with actual byte data. Production Blob handling was unchanged.

wip-tests-03.log: 19 PASS on development WIP, not the final fixed-source gate. All development strict TypeScript invocations, including initial unused import/nullability and test parameter typing errors, are development checks; final fixed gates are separate.

run.py/run-v2.py test_sha256 names their captured artifactWire.test.ts only. Other executed test inputs (including the scope counterexample) are completely bound by source-before/source-after and fixed Git. The new run-v3.py additionally captures all four focused test files by name. scope-red-01 and scope-green-01 used identical complete ArtifactImportNavigation.test.tsx bytes.

wip-scope-extra-01.log (1 FAIL / 3 PASS) is a later test-oracle mistake: the test attempted to find the old author mapping field while the Import UI was correctly suspended/hidden. Its exact test source is preserved as wip-scope-extra-01.test.tsx. The corrected test returns to the original fresh actor to prove the mapping value survives, then re-isolates and explicitly discards it; wip-scope-extra-02.log has 4 PASS. No production change was made for this test correction.
