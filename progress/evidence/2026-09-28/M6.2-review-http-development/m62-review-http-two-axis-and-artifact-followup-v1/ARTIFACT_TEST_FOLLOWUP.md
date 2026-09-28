# Bounded test repair review

No blocking finding in the fixed06c54ed19a0f2cc9125cb6c3fbb75059bf69241f →82ca2052de914bf8ea53cb36a9b8be2c9b64c7bf repair. Only tests/integration/test_artifact_owners.py changes; production code is identical across the probe/repair commits.

The original c2c5ee8 gate is264PASS with **3warnings**, including a real PytestUnhandledThreadExceptionWarning from learning-tutor-worker. Its traceback reaches the test's shared Database.connect monkeypatch. It must not be reported as a clean2dependency-warning pass.

The added concurrent database.workspace_id probe produces an actual deterministic test RED at06c54ed:1FAIL/4warnings. The original shared factory patch rejects that real second-thread read, and the log also records two background-worker exceptions. At82ca205, Database(database.settings) creates a separate connection-factory object for the exact same SQLite path; the checked ImportService alone owns it. Database.__init__ only sets settings/path. Patching that object's connect no longer replaces the application workers' shared factory.

The test still holds the caller's existing transaction with PRAGMA query_only=ON, passes that exact connection to the real owner, compares exact returned bytes/descriptor, and verifies unchanged database dump. A new explicit assertion proves the owner factory itself really rejects connect; a concurrent real app-factory read must succeed. This preserves the old guard while adding its missing isolation boundary, without mocking the owner, weakening assertions, muting warnings or changing timeouts. Relevant requirement: PRODUCT_DESIGN.md:349 and R-29; no contract or migration change.

The same focused case at82ca205 is1PASS/2dependency warnings. All three runs'990 complete engineering inputs independently match their fixed Git blobs before/after, and full raw logs/receipts remain copied privately. The reviewer did not rerun tests. The264-case suite was not repeated on82ca205 here; root's upcoming complete combined gate remains separate evidence. Real provider and human approval NOT_RUN.
