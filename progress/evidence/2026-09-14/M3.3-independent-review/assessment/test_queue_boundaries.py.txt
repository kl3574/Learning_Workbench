"""Synthetic SQLite fault injection, not an exposed arbitrary-SQL capability."""

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.grading import GradingService
from services.api.app.application.imports import ImportService
from services.api.app.application.learning import record_test_submitted
from services.api.app.infrastructure.assessment_repository import AssessmentRepository
from services.api.app.infrastructure.import_worker import ImportWorker
from tests.integration.test_assessment_attempts import storage as initial_storage, start


@pytest.fixture
def storage(tmp_path):
    return initial_storage.__wrapped__(tmp_path)


def submit(storage, key):
    _, identity, _, service = storage
    active = start(storage, mode="open_book", key=f"start-{key}")
    return service.submit(identity, active.id, dm.AttemptSubmit(expected_revision=active.revision), f"submit-{key}")


def real_safe_import(storage):
    database, identity, _, _ = storage
    return ImportService(database).stage(identity, data=b"# Original queue isolation case\n\nSafe synthetic text.\n",
        filename="queue-isolation.md", kind="markdown", key="safe-stage")


def observed_after_bounded_ticks(database, identity, good_id, imported_id):
    worker = ImportWorker(database)
    ticks = []
    try:
        for _ in range(4):
            ticks.append(worker.run_once())
        with database.connect() as connection:
            grade_count = connection.execute("SELECT COUNT(*) FROM grades WHERE attempt_id=?", (good_id,)).fetchone()[0]
            imported = connection.execute("SELECT status FROM ingestion_imports WHERE id=?", (imported_id,)).fetchone()[0]
        return {"valid_grades": grade_count, "safe_import_status": imported, "ticks_reported_work": ticks}
    finally:
        worker.stop()


def test_corrupted_earliest_grading_job_does_not_starve_other_grades_or_safe_import(storage):
    database, identity, _, _ = storage
    bad = submit(storage, "bad")
    good = submit(storage, "good")
    imported = real_safe_import(storage)
    job = GradingService(database).result(identity, bad.id)
    with database.transaction() as connection:
        # The model, allocation and original submission remain valid; only the
        # hash of one queued grading input is damaged by controlled injection.
        connection.execute("UPDATE jobs SET input_sha256=?,created_at='2000-01-01T00:00:00Z' WHERE id=?", ("0" * 64, job.id))
    observed = observed_after_bounded_ticks(database, identity, good.id, imported.import_id)
    assert observed["valid_grades"] == 1 and observed["safe_import_status"] == "preview_ready", observed


def test_damaged_legacy_submission_recovery_does_not_starve_safe_queue(storage):
    database, identity, _, _ = storage
    legacy = start(storage, mode="open_book", key="legacy")
    # A real pre-consumer persisted submit with no grading-job allocation.
    with database.transaction() as connection:
        repo = AssessmentRepository(connection, identity.workspace_id)
        record = repo.submit(repo.load(legacy.id))
        event = record_test_submitted(connection, identity.workspace_id, record.assessment_ref, record.id)
        record = repo.link_submission(record, event)
        legacy_outbox = record.grading_outbox_id
    good = submit(storage, "good")
    imported = real_safe_import(storage)
    with database.transaction() as connection:
        connection.execute("UPDATE outbox SET payload_json=? WHERE id=?", (canonical_bytes({"synthetic_corrupt_submission": True}).decode(), legacy_outbox))
    observed = observed_after_bounded_ticks(database, identity, good.id, imported.import_id)
    assert observed["valid_grades"] == 1 and observed["safe_import_status"] == "preview_ready", observed
