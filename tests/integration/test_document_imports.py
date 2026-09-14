"""Real SQLite document leases, frozen budgets, cancellation, and time limits."""

from contextlib import ExitStack
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

import pytest

from services.api.app.application.imports import ImportService
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.import_dto import ImportCancelRequest, ImportCommitRequest
from services.api.app.infrastructure import document_sandbox as sandbox
from services.api.app.infrastructure import import_worker as worker_module
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.security import SessionIdentity
from tests.document_fixtures import pdf_text_fixture, docx_from_payloads, docx_payloads
from tests.security.test_document_sandbox import arguments


@pytest.fixture
def documents(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    identity = SessionIdentity("session_document", workspace, "learner", "synthetic", "2099-01-01T00:00:00Z")
    worker = ImportWorker(database)
    yield database, ImportService(database), worker, identity
    worker.stop()


def no_publication(database):
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM objects").fetchone()[0] == 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def terminal_count(database, job_id):
    with database.connect() as connection:
        return connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type IN ('completed','failed','cancelled')", (job_id,)).fetchone()[0]


def test_document_worker_uses_staged_budgets_after_configuration_shrinks(documents):
    database, service, _, identity = documents
    staged = service.stage(identity, data=pdf_text_fixture(), filename="synthetic.pdf", kind="pdf", key="stage")
    restarted = Database(replace(database.settings, max_block_characters=10, max_package_files=1, max_upload_bytes=20))
    worker = ImportWorker(restarted)
    try:
        assert worker.run_once()
        preview = service.preview(identity, staged.import_id)
        assert preview.status == "preview_ready"
        drafts = [service.draft(identity, id) for id in preview.preview_refs]
        blocks = [draft for draft in drafts if draft.kind == "block"]
        assert len(blocks) == 2 and all(len(draft.payload.body_markdown) > 10 for draft in blocks)
        for block in blocks:
            locations = {citation.locator for citation in block.payload.citations}
            assert locations
            assert all(warning.locator is None or warning.locator in locations for warning in block.warnings)
        request = ImportCommitRequest(expected_input_sha256=staged.input_sha256,
                                      accepted_warning_codes=sorted({warning.code for warning in preview.warnings if warning.severity == "warning"}), id_mapping=[])
        committed = ImportService(restarted).commit(identity, staged.import_id, request, "commit")
        assert committed.course_refs and terminal_count(database, staged.job.id) == 1
        for block in blocks:
            assert ImportService(restarted).content.body(identity.workspace_id, block.payload.metadata.id, 1)[0] == block.payload.body_markdown.encode()
    finally:
        worker.stop()


def test_document_expired_lease_is_reclaimed_once_and_old_owner_cannot_finalize(documents):
    database, service, worker, identity = documents
    staged = service.stage(identity, data=pdf_text_fixture(), filename="synthetic.pdf", kind="pdf", key="lease")
    stale = worker.claim()
    with database.transaction() as connection:
        connection.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (staged.job.id,))
    restarted = ImportWorker(database)
    try:
        assert restarted.run_once()
        assert service.preview(identity, staged.import_id).status == "preview_ready"
        worker.fail(stale, worker_module.ApiError(422, "STALE_OWNER", "Synthetic old lease"))
        assert service.job(identity, staged.job.id).status == "awaiting_approval"
        assert terminal_count(database, staged.job.id) == 0
        with database.connect() as connection:
            assert connection.execute("SELECT retry_count FROM jobs WHERE id=?", (staged.job.id,)).fetchone()[0] == 1
        no_publication(database)
    finally:
        restarted.stop()


def slow_sandbox_process(channel, data, options, expected_parent):
    """Test-only slow extractor still runs the production namespace/limits command."""
    sandbox.bind_parent_lifetime(expected_parent)
    marker = Path(os.environ["LEARNING_TEST_SANDBOX_MARKER"])
    with tempfile.TemporaryDirectory(prefix="learning-test-extractor-") as directory, ExitStack() as stack:
        entry = Path(directory) / "entry.py"
        entry.write_text("import time\nprint('READY',flush=True)\ntime.sleep(30)\n", encoding="utf-8")
        limits = sandbox.SandboxLimits(wall_seconds=30)
        command, fds = arguments(stack, entry, limits)
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   pass_fds=fds, close_fds=True, start_new_session=True,
                                   env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
        try:
            if process.stdout.readline() != b"READY\n":
                channel.send(("error", "EXTRACTION_ENVIRONMENT_UNAVAILABLE"))
                return
            pids = [process.pid]
            pending = list(pids)
            while pending:
                pid = pending.pop()
                children = [int(value) for value in Path(f"/proc/{pid}/task/{pid}/children").read_text().split()]
                pids.extend(children)
                pending.extend(children)
            marker.write_text(json.dumps(pids), encoding="utf-8")
            process.wait(timeout=30)
        finally:
            sandbox._kill_tree(process)


@pytest.mark.parametrize("action", ["cancel", "timeout", "shutdown"])
def test_worker_stops_real_sandbox_tree_without_late_publication(documents, tmp_path, monkeypatch, action):
    database, service, worker, identity = documents
    marker = tmp_path / "started.json"
    monkeypatch.setenv("LEARNING_TEST_SANDBOX_MARKER", str(marker))
    monkeypatch.setattr(worker_module, "_parse_process", slow_sandbox_process)
    worker.parse_timeout_seconds = 2 if action == "timeout" else 20
    staged = service.stage(identity, data=pdf_text_fixture(), filename="synthetic.pdf", kind="pdf", key=action)
    worker.start()
    deadline = time.monotonic() + 10
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(.02)
    assert marker.exists(), "Real sandbox did not start"
    pids = json.loads(marker.read_text())
    if action == "cancel":
        service.cancel(identity, staged.import_id, ImportCancelRequest(expected_input_sha256=staged.input_sha256), "cancel")
    elif action == "shutdown":
        worker.stop()
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline and any(Path(f"/proc/{pid}").exists() for pid in pids):
        time.sleep(.05)
    assert not any(Path(f"/proc/{pid}").exists() for pid in pids)
    snapshot = service.job(identity, staged.job.id)
    if action == "shutdown":
        assert snapshot.status == "running" and terminal_count(database, staged.job.id) == 0
    else:
        assert snapshot.status == ("cancelled" if action == "cancel" else "failed")
        assert terminal_count(database, staged.job.id) == 1
    if action == "timeout":
        assert snapshot.error.code == "IMPORT_PARSE_TIMEOUT"
    no_publication(database)


def test_docx_cell_inherits_table_and_source_diagnostics_without_neighbor_leak(documents):
    _, service, worker, identity = documents
    payloads = docx_payloads()
    document = payloads["word/document.xml"].decode()
    document = document.replace("<w:t>Synthetic DOCX</w:t>", "<w:t>Synthetic DOCX</w:t><w:drawing/>")
    document = document.replace("<w:sectPr/>", "".join(f"<w:p><w:r><w:t>Scope paragraph {index}</w:t></w:r></w:p>" for index in range(6, 11)))
    payloads["word/document.xml"] = document.encode()
    staged = service.stage(identity, data=docx_from_payloads(payloads), filename="synthetic.docx", kind="docx", key="scope")
    assert worker.run_once()
    preview = service.preview(identity, staged.import_id)
    assert preview.status == "preview_ready"
    drafts = [service.draft(identity, id) for id in preview.preview_refs]
    blocks = [draft for draft in drafts if draft.kind == "block"]
    cells = [draft for draft in blocks if "/w:tc[" in draft.payload.citations[0].locator]
    assert len(cells) == 2
    for cell in cells:
        assert {warning.code for warning in cell.warnings} >= {"DOCX_TABLE_LAYOUT_UNVERIFIED", "DOCX_ORIGINAL_RESTRICTED"}
    first = next(draft for draft in blocks if draft.payload.citations[0].locator.endswith("/w:p[1]"))
    tenth = next(draft for draft in blocks if draft.payload.citations[0].locator.endswith("/w:p[10]"))
    assert "DOCX_IMAGE_NOT_TEX" in {warning.code for warning in first.warnings}
    assert not {"DOCX_IMAGE_NOT_TEX", "DOCX_TABLE_LAYOUT_UNVERIFIED"}.intersection(warning.code for warning in tenth.warnings)
    assert "DOCX_TABLE_LAYOUT_UNVERIFIED" in {warning.code for warning in preview.warnings}
