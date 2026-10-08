import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

MODULE = Path(__file__).parents[1] / "e2e" / "server_stage_observer.py"
spec = importlib.util.spec_from_file_location("owned_server_stage_observer", MODULE)
observer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = observer
spec.loader.exec_module(observer)

class CollectorBoundaryTests(unittest.TestCase):
    def test_private_fields_and_unknown_status_never_enter_bounded_output(self):
        collector = observer.Collector(limit=2, clock=lambda: 100)
        collector.arm()
        collector.emit(observer.Phase.CLAIM, observer.Edge.ENTER)
        collector.emit("attempt_SECRET", observer.Edge.ENTER)
        collector.emit(observer.Phase.CLAIM, observer.Edge.ENTER, status="answer_SECRET")
        collector.emit(observer.Phase.CLAIM, observer.Edge.ENTER)
        collector.emit(observer.Phase.CLAIM, observer.Edge.ENTER)
        value = collector.freeze()
        encoded = json.dumps(value)
        self.assertNotIn("SECRET", encoded)
        self.assertEqual(len(value["events"]), 2)
        self.assertEqual(value["dropped"], 1)
        self.assertEqual(value["diagnostic_errors"], 2)

    def test_nested_lock_admission_preserves_output_order_and_bound(self):
        collector = observer.Collector(limit=2, clock=lambda: 100)
        collector.arm()

        class AdmissionLock:
            def __init__(self):
                self.first = True
                self.locked = False
                self.requests = []

            def acquire(self, *, blocking):
                self.requests.append(blocking)
                if self.first:
                    self.first = False
                    collector.emit(observer.Phase.RESULT, observer.Edge.ENTER)
                if self.locked:
                    return False
                self.locked = True
                return True

            def release(self):
                self.locked = False

        lock = AdmissionLock()
        collector._lock = lock
        collector.emit(observer.Phase.CLAIM, observer.Edge.ENTER)
        collector.emit(observer.Phase.FINISH, observer.Edge.EXIT)
        value = collector.freeze()
        self.assertEqual([event["phase"] for event in value["events"]],
                         ["get-result", "grading-claim"])
        self.assertEqual([event["seq"] for event in value["events"]], [1, 2])
        self.assertEqual(value["dropped"], 1)
        self.assertEqual(value["diagnostic_errors"], 0)
        self.assertEqual(value["capture_state"], "frozen")
        self.assertTrue(all(request is False for request in lock.requests))
        self.assertTrue(all(set(event) == {"seq", "elapsed_ns", "phase", "edge"}
                            for event in value["events"]))



class Clock:
    def __init__(self):
        self.now = 1000
    def __call__(self):
        return self.now

class BindingTests(unittest.TestCase):
    def fixture(self, *, limit=512):
        clock = Clock()
        trace = []
        class Database:
            @contextmanager
            def transaction(self, **kwargs):
                trace.append(("begin", kwargs))
                clock.now += 7
                try:
                    yield object()
                except BaseException:
                    trace.append("rollback")
                    raise
                else:
                    clock.now += 3
                    trace.append("commit")
        database = Database()
        class Repository:
            def enqueue(self, private):
                trace.append("enqueue")
                return private
            def latest_job(self):
                trace.append("read-existing-row")
                return {"status": "queued", "id": "JOB_SECRET", "input_json": "ANSWER_SECRET"}
        repository = Repository()
        class Service:
            def __init__(self, db):
                self.database = db
                self.failure = None
                self.value = object()
            def regrade(self, *args, **kwargs):
                with self.database.transaction():
                    if self.failure:
                        raise self.failure
                    repository.enqueue("PRIVATE_REASON_SECRET")
                return self.value
            def result(self):
                with self.database.transaction(immediate=False):
                    value = repository.latest_job()
                    clock.now += 5
                with self.database.transaction():
                    clock.now += 2
                return value
        service = Service(database)
        def node(name):
            def run_once():
                trace.append(name)
                clock.now += 13
                return False
            return SimpleNamespace(run_once=run_once)
        class Grading:
            def recover(self):
                trace.append("recover")
            def claim(self):
                trace.append("claim")
                with database.transaction():
                    clock.now += 11
                return object()
            def compute(self, lease):
                trace.append("compute")
                clock.now += 17
                return object(), object()
            def finish(self, lease, result, audit):
                trace.append("finish")
            def run_once(self):
                self.recover()
                lease = self.claim()
                result, audit = self.compute(lease)
                self.finish(lease, result, audit)
        class Worker:
            def __init__(self):
                self.evidence_recovery = node("evidence")
                self.recommendations = node("recommendation")
                self.retrieval = node("retrieval")
                self.grading = Grading()
            def run_once(self):
                self.evidence_recovery.run_once()
                self.recommendations.run_once()
                self.retrieval.run_once()
                self.grading.run_once()
                trace.append("import")
                return False
        worker = Worker()
        collector = observer.Collector(limit=limit, clock=clock)
        binding = observer.OwnedBindings(collector, database, worker, Service, Repository)
        self.assertTrue(binding.install())
        self.addCleanup(binding.restore)
        return SimpleNamespace(clock=clock, trace=trace, db=database, service=service, worker=worker,
                               collector=collector, binding=binding, Service=Service, Repository=Repository)

    def test_same_server_clock_separates_claim_reservation_from_original_work(self):
        f = self.fixture()
        f.collector.arm()
        self.assertIs(f.worker.run_once(), False)
        self.assertEqual([x for x in f.trace if isinstance(x, str) and x not in ("commit",)],
                         ["evidence", "recommendation", "retrieval", "recover", "claim", "compute", "finish", "import"])
        value = f.collector.freeze()
        ready = [e for e in value["events"] if e["phase"] == "grading-claim" and e["edge"] == "transaction-ready"]
        self.assertEqual([e["duration_ns"] for e in ready], [7])
        exits = [e for e in value["events"] if e["phase"] == "grading-claim" and e["edge"] == "exit"]
        self.assertEqual([e["duration_ns"] for e in exits], [21, 21])
        self.assertEqual(value["diagnostic_errors"], 0)

    def test_enqueue_committed_is_after_original_commit_not_enqueue_call(self):
        f = self.fixture()
        def commit_observed(method, *args, **kwargs):
            if method == "emit" and args[1] is observer.Edge.COMMITTED:
                self.assertEqual(f.trace[-1], "commit")
            return getattr(f.collector, method)(*args, **kwargs)
        f.binding._safe = commit_observed
        self.assertIs(f.service.regrade("ACTOR_SECRET", attempt="ATTEMPT_SECRET"), f.service.value)
        events = f.collector.freeze()["events"]
        self.assertEqual(sum(e["edge"] == "new-enqueue-committed" for e in events), 1)
        self.assertNotIn("SECRET", json.dumps(events))

    def test_existing_get_wal_status_precedes_policy_and_adds_no_read(self):
        f = self.fixture()
        f.collector.arm()
        result = f.service.result()
        self.assertEqual(result["id"], "JOB_SECRET")
        self.assertEqual(f.trace.count("read-existing-row"), 1)
        self.assertEqual(f.trace[0], ("begin", {"immediate": False}))
        self.assertEqual(f.trace[3], ("begin", {}))
        events = f.collector.freeze()["events"]
        statuses = [e for e in events if e["edge"] == "existing-status-read"]
        self.assertEqual([e["status"] for e in statuses], ["queued"])
        status_seq = statuses[0]["seq"]
        policy_ready = next(e["seq"] for e in events if e["phase"] == "result-policy" and e["edge"] == "transaction-ready")
        self.assertLess(status_seq, policy_ready)
        self.assertNotIn("SECRET", json.dumps(events))

    def test_unarmed_read_and_other_database_owner_remain_unobserved(self):
        f = self.fixture()
        f.service.result()
        other = f.Service(f.db.__class__())
        self.assertIs(other.regrade(), other.value)
        self.assertFalse(f.collector.freeze()["armed"])

    def test_clock_and_event_faults_preserve_original_return(self):
        f = self.fixture()
        def broken(*args, **kwargs):
            raise OSError("KEY_SECRET")
        f.collector.emit = broken
        f.collector._clock = broken
        self.assertIs(f.service.regrade(), f.service.value)
        self.assertEqual(f.trace[-1], "commit")

    def test_faults_do_not_replace_original_exception_or_rollback(self):
        f = self.fixture()
        primary = RuntimeError("ORIGINAL_BODY_SECRET")
        f.service.failure = primary
        def broken(*args, **kwargs):
            raise ValueError("DIAGNOSTIC_HEADER_SECRET")
        f.collector.emit = broken
        with self.assertRaises(RuntimeError) as received:
            f.service.regrade()
        self.assertIs(received.exception, primary)
        self.assertEqual(f.trace[-1], "rollback")

    def test_event_overflow_does_not_skip_original_calls(self):
        f = self.fixture(limit=1)
        self.assertIs(f.service.regrade(), f.service.value)
        f.worker.run_once()
        self.assertEqual(f.trace[-1], "import")
        value = f.collector.freeze()
        self.assertEqual(len(value["events"]), 1)
        self.assertGreater(value["dropped"], 0)

    def test_failed_install_restores_already_wrapped_owner(self):
        f = self.fixture()
        f.binding.restore()
        original = f.worker.run_once.__func__
        f.worker.grading = object()
        self.assertFalse(f.binding.install())
        self.assertIs(f.worker.run_once.__func__, original)
        self.assertNotIn("run_once", vars(f.worker))

    def test_unexpected_original_keyword_is_not_swallowed_by_wrapper(self):
        f = self.fixture()
        original = f.Repository.enqueue
        with self.assertRaises(TypeError):
            original(f.Repository(), _phase="SECRET")
        self.assertNotIn("SECRET", json.dumps(f.collector.freeze()))

class CleanupTests(unittest.TestCase):
    def test_frozen_output_is_immutable_and_has_no_fabricated_cleanup_claim(self):
        collector = observer.Collector(clock=lambda: 100)
        collector.arm()
        collector.emit(observer.Phase.CLAIM, observer.Edge.ENTER)
        first = collector.freeze()
        first["events"].clear()
        collector.emit(observer.Phase.CLAIM, observer.Edge.ENTER)
        second = collector.freeze()
        self.assertEqual(len(second["events"]), 1)
        self.assertEqual(second["finally_marker"], "collector-freeze")

    def test_cleanup_writer_failure_is_nonthrowing_and_existing_output_is_preserved(self):
        collector = observer.Collector(clock=lambda: 100)
        def failed_writer(*args, **kwargs):
            raise OSError("PRIVATE_OUTPUT_PATH_SECRET")
        self.assertFalse(collector.save(Path("unused"), writer=failed_writer))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "metadata.json"
            target.write_text("prior immutable output")
            self.assertFalse(collector.save(target))
            self.assertEqual(target.read_text(), "prior immutable output")

    def test_event_and_finalizer_lock_contention_never_waits_or_claims_complete(self):
        collector = observer.Collector(clock=lambda: 100)
        collector.arm()
        collector._lock.acquire()
        try:
            collector.emit(observer.Phase.CLAIM, observer.Edge.ENTER)
            value = collector.freeze()
            self.assertEqual(value["capture_state"], "finalize-contended")
            self.assertEqual(value["dropped"], 1)
        finally:
            collector._lock.release()

if __name__ == "__main__":
    unittest.main()
