"""Durable import/worker/confirmation tests with synthetic inputs and real SQLite."""

from dataclasses import replace
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_STORED
import json

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.validation import ENTITY_MODELS, parse_manifest
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.import_parsing import parse_import
from services.api.app.application.imports import ImportService
from services.api.app.config import Settings
from services.api.app.database import Database
from services.api.app.import_dto import ImportCancelRequest, ImportCommitRequest, ImportIdMapping, JobCancelRequest
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.infrastructure.security import SessionIdentity

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "synthetic"


@pytest.fixture
def imports(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    identity = SessionIdentity("session_synthetic", workspace, "learner", "synthetic_csrf", "2099-01-01T00:00:00Z")
    service = ImportService(database)
    worker = ImportWorker(database)
    yield database, service, worker, identity
    worker.stop()


def author(identity):
    return replace(identity, role="author")


def staged_ready(imports, *, data=b"# Synthetic lesson\n\n$x^2$ is nonnegative.\n", filename="lesson.md", kind="markdown", target=None, key="stage"):
    database, service, worker, identity = imports
    staged = service.stage(identity, data=data, filename=filename, kind=kind, target_course_id=target, key=key)
    assert worker.run_once()
    preview = service.preview(author(identity), staged.import_id)
    assert preview.status == "preview_ready", preview.model_dump()
    return staged, preview


def decision(staged, preview, mappings=()):
    return ImportCommitRequest(expected_input_sha256=staged.input_sha256,
        accepted_warning_codes=sorted({warning.code for warning in preview.warnings if warning.severity == "warning"}), id_mapping=list(mappings))


def sql_count(database, table):
    assert table in {"objects", "revisions", "solutions", "drafts", "jobs", "sources", "ingestion_imports", "notes_index"}
    with database.connect() as connection:
        return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_stage_is_durable_and_idempotent_without_publishing_then_real_worker_preview(imports):
    database, service, worker, identity = imports
    data = b"# Durable title\n\nOriginal source with $x$.\n"
    staged = service.stage(identity, data=data, filename="../unsafe/name.md", kind="markdown", key="same")
    assert sql_count(database, "objects") == sql_count(database, "revisions") == 0
    assert service.preview(identity, staged.import_id).status == "staged"
    assert service.job(identity, staged.job.id).status == "queued"
    assert service.stage(identity, data=data, filename="../unsafe/name.md", kind="markdown", key="same") == staged
    assert sql_count(database, "jobs") == sql_count(database, "sources") == 1
    with pytest.raises(ApiError) as error:
        service.stage(identity, data=b"different", filename="name.md", kind="markdown", key="same")
    assert error.value.code == "IDEMPOTENCY_CONFLICT"
    restarted = ImportWorker(Database(database.settings))
    assert restarted.run_once()
    preview = service.preview(identity, staged.import_id)
    assert preview.status == "preview_ready" and preview.preview_refs
    snapshot = service.job(identity, staged.job.id)
    assert snapshot.status == "awaiting_approval" and snapshot.result_refs == []
    assert sql_count(database, "objects") == 0
    block = next(service.draft(identity, id) for id in preview.preview_refs if service.draft(identity, id).kind == "block")
    assert any("Original source" in candidate.payload.body_markdown
               for candidate in (service.draft(identity, id) for id in preview.preview_refs) if candidate.kind == "block")
    assert block.candidate_sha256 == metadata_sha256(block.payload.metadata)
    source = service.source(identity, block.payload.source_id)
    assert source.artifact.filename == "name.md"
    assert service.download(identity, source.artifact.artifact_id)[0] == data
    assert source.parser_version


def test_explicit_confirmation_publishes_once_receipt_and_terminal_event_atomically(imports):
    database, service, _, identity = imports
    staged, preview = staged_ready(imports)
    with pytest.raises(ApiError) as error:
        service.commit(identity, staged.import_id, ImportCommitRequest(expected_input_sha256=staged.input_sha256, accepted_warning_codes=[], id_mapping=[]), "unacknowledged")
    assert error.value.code == "IMPORT_WARNINGS_UNACKNOWLEDGED"
    request = decision(staged, preview)
    result = service.commit(identity, staged.import_id, request, "commit")
    assert len(result.course_refs) == 1
    assert service.commit(identity, staged.import_id, request, "commit") == result
    assert service.commit(identity, staged.import_id, request, "same_decision_new_key") == result
    snapshot = service.job(identity, staged.job.id)
    assert snapshot.status == "completed" and snapshot.result_refs == result.course_refs
    assert service.preview(identity, staged.import_id).status == "committed"
    receipt, artifact = service.download(identity, result.migration_receipt_id)
    assert b'"mathematical":"NOT_RUN"' in receipt and artifact.media_type == "application/json"
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type IN ('completed','failed','cancelled')", (staged.job.id,)).fetchone()[0] == 1
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    with pytest.raises(ApiError) as error:
        service.cancel(identity, staged.import_id, ImportCancelRequest(expected_input_sha256=staged.input_sha256), "cancel_committed")
    assert error.value.code == "IMPORT_ALREADY_COMMITTED"


def test_cancel_queued_and_cancel_parsing_never_publish_and_old_lease_cannot_finish(imports):
    database, service, worker, identity = imports
    staged = service.stage(identity, data=b"synthetic", filename="a.txt", kind="text", key="queued")
    service.cancel(identity, staged.import_id, ImportCancelRequest(expected_input_sha256=staged.input_sha256), "cancel")
    assert worker.run_once() is False
    assert service.job(identity, staged.job.id).status == "cancelled"
    staged2 = service.stage(identity, data=b"synthetic second", filename="b.txt", kind="text", key="parsing")
    lease = worker.claim()
    assert lease
    data, options = worker._input(lease)
    parsed = parse_import(data, **options)
    snapshot = service.job(identity, staged2.job.id)
    result = service.cancel_job(identity, staged2.job.id, JobCancelRequest(expected_revision=snapshot.revision), "cancel_job")
    assert result.status == "cancelled"
    assert worker.complete_preview(lease, parsed) is False
    assert sql_count(database, "objects") == sql_count(database, "drafts") == 0
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM job_events WHERE type='cancelled'").fetchone()[0] == 2


def test_expired_lease_reclaimed_after_restart_without_duplicate_preview(imports):
    database, service, worker, identity = imports
    staged = service.stage(identity, data=b"recoverable source", filename="recover.txt", kind="text", key="lease")
    first = worker.claim()
    assert first
    data, options = worker._input(first)
    parsed = parse_import(data, **options)
    with database.transaction() as connection:
        connection.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (staged.job.id,))
    restarted = ImportWorker(database)
    assert restarted.run_once()
    count = sql_count(database, "drafts")
    assert count > 0
    assert worker.complete_preview(first, parsed) is False
    assert sql_count(database, "drafts") == count
    assert restarted.run_once() is False
    with database.connect() as connection:
        assert connection.execute("SELECT retry_count FROM jobs WHERE id=?", (staged.job.id,)).fetchone()[0] == 1


def test_commit_rollback_preserves_preview_and_retry_completes_once(imports):
    database, service, _, identity = imports
    staged, preview = staged_ready(imports)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER fail_terminal BEFORE INSERT ON job_events WHEN NEW.type='completed' BEGIN SELECT RAISE(ABORT,'synthetic private failure'); END")
    with pytest.raises(ApiError) as error:
        service.commit(identity, staged.import_id, decision(staged, preview), "commit")
    assert error.value.status == 503 and "synthetic" not in error.value.message
    assert sql_count(database, "objects") == 0
    assert service.preview(identity, staged.import_id).status == "preview_ready"
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER fail_terminal")
    assert service.commit(identity, staged.import_id, decision(staged, preview), "commit").course_refs


def test_author_package_private_answers_and_original_never_leak_to_learner(imports):
    database, service, _, identity = imports
    raw = (FIXTURES / "course-author.learnpack.zip").read_bytes()
    staged, preview = staged_ready(imports, data=raw, filename="author.learnpack.zip", kind="learnpack")
    with pytest.raises(ApiError) as error:
        service.preview(identity, staged.import_id)
    assert error.value.status == 403
    with pytest.raises(ApiError):
        service.commit(identity, staged.import_id, decision(staged, preview), "learner_commit")
    block = next(service.draft(author(identity), id) for id in preview.preview_refs if service.draft(author(identity), id).kind == "block")
    source = service.source(author(identity), block.payload.source_id)
    with pytest.raises(ApiError):
        service.download(identity, source.artifact.artifact_id)
    assert service.download(author(identity), source.artifact.artifact_id)[0] == raw
    result = service.commit(author(identity), staged.import_id, decision(staged, preview), "author_commit")
    assert result.course_refs
    with database.connect() as connection:
        solutions = connection.execute("SELECT * FROM solutions").fetchall()
        assert solutions and all(row["review_status"] == "needs_review" for row in solutions)
        assert all('"review_status":"needs_review"' in row["private_json"] for row in solutions)
        assert all("accepted_answers" not in row[0] for row in connection.execute("SELECT metadata_json FROM revisions"))
        metadata = connection.execute("SELECT metadata_json FROM sources").fetchone()[0]
        assert "untrusted_quality_receipt" in metadata and "symbols" in metadata
    with pytest.raises(ApiError):
        service.download(identity, result.migration_receipt_id)


def test_learner_package_collision_requires_mapping_and_rehashes_all_refs(imports):
    database, service, _, identity = imports
    raw = (FIXTURES / "course-learner.learnpack.zip").read_bytes()
    first, preview = staged_ready(imports, data=raw, filename="learner.learnpack.zip", kind="learnpack", key="first")
    service.commit(identity, first.import_id, decision(first, preview), "first_commit")
    second, preview2 = staged_ready(imports, data=raw, filename="learner.learnpack.zip", kind="learnpack", key="second")
    request = decision(second, preview2)
    with pytest.raises(ApiError) as error:
        service.commit(identity, second.import_id, request, "collision")
    assert error.value.code == "IMPORT_ID_COLLISION"
    parsed = parse_import(raw, kind="learnpack", filename="learner.learnpack.zip", source_id="source_synthetic")
    mapping = [ImportIdMapping(old_id=id, new_id=f"copy_{id}") for id in sorted({value.id for value in parsed.objects})]
    result = service.commit(identity, second.import_id, decision(second, preview2, mapping), "mapped")
    assert all(ref.id.startswith("copy_") for ref in result.course_refs)
    for old in parsed.objects:
        new = service.content.read(identity.workspace_id, old.entity, f"copy_{old.id}", old.revision)
        if isinstance(new, dm.Lesson):
            assert all(ref.id.startswith("copy_") for ref in new.block_refs)
            for ref in new.block_refs:
                block = service.content.read(identity.workspace_id, "block", ref.id, ref.revision)
                assert metadata_sha256(block) == ref.sha256
    assert sql_count(database, "objects") == len(parsed.objects) * 2


def test_append_to_frozen_target_adds_new_revision_and_conflict_never_overwrites(imports):
    database, service, _, identity = imports
    first, preview = staged_ready(imports)
    original = service.commit(identity, first.import_id, decision(first, preview), "first_commit").course_refs[0]
    staged, preview2 = staged_ready(imports, data=b"# Extra lesson\n\nA second body.\n", key="second", target=original.id)
    result = service.commit(identity, staged.import_id, decision(staged, preview2), "append")
    assert len(result.course_refs) == 1 and result.course_refs[0].id == original.id and result.course_refs[0].revision == 2
    old = service.content.read(identity.workspace_id, "course", original.id, 1)
    new = service.content.read(identity.workspace_id, "course", original.id, 2)
    assert len(new.lesson_refs) > len(old.lesson_refs) and new.lesson_refs[:len(old.lesson_refs)] == old.lesson_refs
    third, preview3 = staged_ready(imports, data=b"Third content", filename="third.txt", kind="text", key="third", target=original.id)
    update = new.model_copy(update={"revision": 3, "title": "Concurrent title"})
    service.content.publish(identity.workspace_id, [update], {})
    with pytest.raises(ApiError) as error:
        service.commit(identity, third.import_id, decision(third, preview3), "stale_append")
    assert error.value.code == "IMPORT_TARGET_CHANGED"
    assert service.content.current(identity.workspace_id, original.id).revision == 3
    assert service.preview(identity, third.import_id).status == "preview_ready"


def test_same_workspace_guard_and_cross_workspace_reads_writes(imports):
    database, service, worker, identity = imports
    staged, preview = staged_ready(imports)
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('other','Synthetic','2026-09-14T00:00:00Z')")
    other = replace(identity, workspace_id="other")
    for action in [lambda: service.preview(other, staged.import_id), lambda: service.job(other, staged.job.id),
                   lambda: service.draft(other, preview.preview_refs[0]),
                   lambda: service.commit(other, staged.import_id, decision(staged, preview), "other")]:
        with pytest.raises(ApiError) as error:
            action()
        assert error.value.status == 404
    raw = (FIXTURES / "course-learner.learnpack.zip").read_bytes()
    parsed = parse_import(raw, kind="learnpack", filename="course.zip", source_id="source_synthetic")
    service.content.publish(identity.workspace_id, parsed.objects, parsed.bodies)
    assessment = next(value for value in parsed.objects if isinstance(value, dm.AssessmentBlueprint))
    with database.transaction() as connection:
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES('attempt',?,?,?,'independent','{}','[]','[]','active',1,'2026-09-14T00:00:00Z')", (identity.workspace_id, assessment.id, assessment.revision))
    for active_identity in [identity, author(identity)]:
        for action in [lambda: service.stage(active_identity, data=b"blocked", filename="a.txt", kind="text", key="blocked"),
                       lambda: service.preview(active_identity, staged.import_id),
                       lambda: service.job(active_identity, staged.job.id),
                       lambda: service.draft(active_identity, preview.preview_refs[0]),
                       lambda: service.commit(active_identity, staged.import_id, decision(staged, preview), "blocked")]:
            with pytest.raises(ApiError) as error:
                action()
            assert error.value.code == "ASSESSMENT_ACTIVE"
    assert worker.claim() is None


def test_corrupt_original_worker_failure_is_terminal_without_content(imports):
    database, service, worker, identity = imports
    staged = service.stage(identity, data=b"source", filename="a.txt", kind="text", key="corrupt")
    path = database.settings.data_dir / "blobs" / staged.input_sha256[:2] / staged.input_sha256
    path.write_bytes(b"damaged")
    assert worker.run_once()
    snapshot = service.job(identity, staged.job.id)
    assert snapshot.status == "failed" and snapshot.error.code == "CONTENT_HASH_MISMATCH"
    assert sql_count(database, "objects") == 0
    assert worker.run_once() is False


@pytest.mark.parametrize("filename,kind", [("prefixed.learnpack.zip", "auto"), ("plain.txt", "auto"), ("plain.md", "markdown")])
def test_prefixed_author_zip_cannot_download_as_learner_before_or_after_parse(imports, filename, kind):
    database, service, worker, identity = imports
    data = b"SYNTHETIC PREFIX\n" + (FIXTURES / "course-author.learnpack.zip").read_bytes()
    staged = service.stage(identity, data=data, filename=filename, kind=kind, key="prefixed")
    with database.connect() as connection:
        artifact_id = connection.execute("SELECT id FROM artifacts WHERE profile='import_original'").fetchone()[0]
    with pytest.raises(ApiError) as error:
        service.download(identity, artifact_id)
    assert error.value.status == 403
    assert service.download(author(identity), artifact_id)[0] == data
    assert worker.run_once()
    with pytest.raises(ApiError):
        service.download(identity, artifact_id)
    snapshot = service.job(author(identity), staged.job.id)
    if kind == "markdown":
        assert snapshot.status == "failed" and snapshot.error.code == "IMPORT_FORMAT_MISMATCH"
    else:
        assert snapshot.status == "failed" and snapshot.error.code == "PACKAGE_ENVELOPE_UNCLAIMED"


@pytest.mark.parametrize("kind,filename,data,code", [
    ("pdf", "sample.pdf", b"%PDF synthetic", "PDF_MALFORMED"),
    ("docx", "sample.docx", b"not_a_docx", "DOCX_CONTAINER_UNSUPPORTED"),
])
def test_damaged_document_retains_explicit_parser_error_without_false_preview(imports, kind, filename, data, code):
    database, service, worker, identity = imports
    staged = service.stage(identity, data=data, filename=filename, kind=kind, key="unsupported")
    assert worker.run_once()
    snapshot = service.job(author(identity), staged.job.id)
    assert snapshot.status == "failed" and snapshot.error.code == code
    assert service.preview(author(identity), staged.import_id).preview_refs == []
    assert sql_count(database, "objects") == 0


def reference(value):
    return dm.ContentRef(entity=value.entity, id=value.id, revision=value.revision, sha256=metadata_sha256(value))


def synthetic_tree(revision=1):
    body = f"Synthetic 🧠 body {revision}\n".encode()
    block = dm.ContentBlock(id="block_custom", revision=revision, title="Custom block", kind="text", body_path=f"content/body_{revision}.md", body_sha256=sha256_bytes(body))
    lesson = dm.Lesson(id="lesson_custom", revision=revision, title="Custom lesson", objectives=[], block_refs=[reference(block)])
    course = dm.Course(id="course_custom", revision=revision, title="Custom course", audience="Synthetic", lesson_refs=[reference(lesson)])
    return [block, lesson, course], {block.body_path: body}


def package_bytes(objects, bodies, *, symbols=(), asset=None, budgets=ImportBudgets()):
    root = max((value for value in objects if isinstance(value, dm.Course)), key=lambda value: value.revision)
    payloads = {f"metadata/{value.entity}_{value.id}_{value.revision}.json": canonical_bytes(value) for value in objects if value != root}
    payloads["course.json"] = canonical_bytes(root)
    payloads["symbols.json"] = canonical_bytes([value.model_dump(mode="json") for value in symbols])
    payloads["sources/citations.json"] = b"[]"
    payloads["checks/quality-receipt.json"] = b'{"mathematical":"APPROVED","fixture_only":true}'
    payloads.update(bodies)
    if asset is not None:
        payloads["assets/synthetic.txt"] = asset
    manifest = parse_manifest({"package_id": "package_custom", "profile": "learner", "created_at": "2026-09-14T00:00:00Z", "files": [
        dm.FileEntry(path=path, size=len(data), sha256=sha256_bytes(data), media_type="text/plain" if path.endswith(".txt") else "text/markdown" if path.endswith(".md") else "application/json", visibility="learner").model_dump(mode="python")
        for path, data in payloads.items()
    ]}, budgets=budgets)
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        archive.writestr("manifest.json", canonical_bytes(manifest))
        for path, data in payloads.items():
            archive.writestr(path, data)
    return output.getvalue()


@pytest.mark.parametrize("quote,state", [("Synthetic", "exact"), ("WrongText", "stale")])
def test_notes_import_to_authorized_workspace_with_verified_or_stale_anchor(imports, quote, state):
    database, service, _, identity = imports
    values, bodies = synthetic_tree()
    note = dm.Note(id="note_custom", revision=1, workspace_id="workspace_external", markdown="Synthetic personal note",
                   anchor=dm.Selection(ref=reference(values[0]), exact_quote=quote, start_codepoint=0, end_codepoint=9))
    raw = package_bytes([*values, note], bodies)
    staged, preview = staged_ready(imports, data=raw, filename="notes.learnpack.zip", kind="learnpack")
    result = service.commit(identity, staged.import_id, decision(staged, preview), "note_commit")
    assert result.course_refs
    with database.connect() as connection:
        row = connection.execute("SELECT metadata_json FROM revisions WHERE object_id='note_custom'").fetchone()
        stored = dm.Note.model_validate_json(row[0])
        assert stored.workspace_id == identity.workspace_id and stored.anchor_state == state
        assert connection.execute("SELECT anchor_state FROM notes_index WHERE note_id='note_custom'").fetchone()[0] == state
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    with pytest.raises(ApiError):
        service.content.read(identity.workspace_id, "note", note.id, 1)
    receipt = json.loads(service.download(identity, result.migration_receipt_id)[0])
    assert receipt["workspace_remapped_note_ids"] == [note.id]


def test_package_multiple_exact_revisions_preserves_history_and_current_maximum(imports):
    database, service, _, identity = imports
    old, old_bodies = synthetic_tree(1)
    new, new_bodies = synthetic_tree(2)
    raw = package_bytes([*new, *old], old_bodies | new_bodies)
    staged, preview = staged_ready(imports, data=raw, filename="history.learnpack.zip", kind="learnpack")
    result = service.commit(identity, staged.import_id, decision(staged, preview), "history_commit")
    assert {ref.revision for ref in result.course_refs} == {1, 2}
    for value in old + new:
        assert service.content.read(identity.workspace_id, value.entity, value.id, value.revision) == value
        assert service.content.current(identity.workspace_id, value.id).revision == 2
    assert service.content.body(identity.workspace_id, "block_custom", 1)[0] == old_bodies[old[0].body_path]
    assert sql_count(database, "revisions") == 6


def test_course_history_exact_concepts_bind_old_and_new_versions_without_current_rebinding(imports):
    database, service, _, identity = imports
    old, old_bodies = synthetic_tree(1)
    new, new_bodies = synthetic_tree(2)
    b1 = dm.Concept(id="concept_b", revision=1, title="B1")
    b2 = dm.Concept(id="concept_b", revision=2, title="B2")
    a1 = dm.Concept(id="concept_a", revision=1, title="A1", prerequisite_ids=[b1.id])
    a2 = dm.Concept(id="concept_a", revision=2, title="A2", prerequisite_ids=[b2.id])
    old[-1] = old[-1].model_copy(update={"concept_refs": [reference(a1), reference(b1)]})
    new[-1] = new[-1].model_copy(update={"concept_refs": [reference(a2), reference(b2)]})
    raw = package_bytes([*new, a2, b2, *old, a1, b1], old_bodies | new_bodies)
    staged, preview = staged_ready(imports, data=raw, filename="concept-history.learnpack.zip", kind="learnpack")
    service.commit(identity, staged.import_id, decision(staged, preview), "concept_history")
    with database.connect() as connection:
        for version in (1, 2):
            frozen = connection.execute("SELECT target_revision FROM object_dependencies WHERE owner_id='concept_a' AND owner_revision=? AND target_id='concept_b'", (version,)).fetchone()
            assert frozen[0] == version


def test_assets_raw_quality_and_symbol_references_survive_mapping(imports):
    database, service, _, identity = imports
    values, bodies = synthetic_tree()
    symbol = dm.Symbol(id="symbol_x", tex="x", meaning="Synthetic symbol", domain="real", dimension="scalar", scope="lesson_custom", first_definition=reference(values[0]))
    raw = package_bytes(values, bodies, symbols=[symbol], asset=b"synthetic passive resource")
    staged, preview = staged_ready(imports, data=raw, filename="assets.learnpack.zip", kind="learnpack")
    mapping = [ImportIdMapping(old_id=value.id, new_id="mapped_" + value.id) for value in values]
    service.commit(identity, staged.import_id, decision(staged, preview, mapping), "asset_commit")
    with database.connect() as connection:
        metadata = json.loads(connection.execute("SELECT metadata_json FROM sources").fetchone()[0])
    actual_symbol = dm.Symbol.model_validate(metadata["symbols"][0])
    assert actual_symbol.scope == "mapped_lesson_custom" and actual_symbol.first_definition.id == "mapped_block_custom"
    block = service.content.read(identity.workspace_id, "block", "mapped_block_custom", 1)
    assert actual_symbol.first_definition.sha256 == metadata_sha256(block)
    assert service.download(identity, metadata["assets"]["assets/synthetic.txt"]["artifact_id"])[0] == b"synthetic passive resource"
    assert service.download(identity, metadata["untrusted_quality_receipt"]["artifact_id"])[0] == b'{"mathematical":"APPROVED","fixture_only":true}'
    assert metadata["original_symbols"][0]["scope"] == "lesson_custom"


def test_note_course_anchor_is_rebound_when_import_appends_to_existing_course(imports):
    database, service, _, identity = imports
    initial, initial_preview = staged_ready(imports)
    target = service.commit(identity, initial.import_id, decision(initial, initial_preview), "initial").course_refs[0]
    values, bodies = synthetic_tree()
    note = dm.Note(id="note_course", revision=1, workspace_id="external_workspace", markdown="Synthetic note",
                   anchor=dm.Selection(ref=reference(values[-1]), exact_quote="", start_codepoint=0, end_codepoint=0), anchor_state="unresolved")
    raw = package_bytes([*values, note], bodies)
    staged, preview = staged_ready(imports, data=raw, filename="append-note.learnpack.zip", kind="learnpack", target=target.id, key="append_stage")
    result = service.commit(identity, staged.import_id, decision(staged, preview), "append_note")
    with database.connect() as connection:
        note = dm.Note.model_validate_json(connection.execute("SELECT metadata_json FROM revisions WHERE object_id='note_course'").fetchone()[0])
    assert note.anchor.ref == result.course_refs[0] and note.anchor_state == "unresolved"


def test_parse_timeout_terminates_process_and_has_no_partial_publication(imports):
    database, service, worker, identity = imports
    staged = service.stage(identity, data=b"timeout source", filename="timeout.txt", kind="text", key="timeout")
    worker.parse_timeout_seconds = 0.000001
    assert worker.run_once()
    snapshot = service.job(identity, staged.job.id)
    assert snapshot.status == "failed" and snapshot.error.code == "IMPORT_PARSE_TIMEOUT"
    assert sql_count(database, "objects") == sql_count(database, "drafts") == 0


def test_error_warning_cannot_be_acknowledged_and_cancellation_is_idempotent(imports):
    database, service, worker, identity = imports
    staged = service.stage(identity, data=b"synthetic source", filename="error.txt", kind="text", key="error")
    lease = worker.claim()
    data, options = worker._input(lease)
    parsed = parse_import(data, **options)
    parsed = replace(parsed, warnings=(*parsed.warnings, dm.Warning(code="UNRESOLVED_REFERENCE", message="Synthetic unresolved reference", severity="error")))
    assert worker.complete_preview(lease, parsed)
    preview = service.preview(identity, staged.import_id)
    request = decision(staged, preview).model_copy(update={"accepted_warning_codes": sorted({warning.code for warning in preview.warnings})})
    with pytest.raises(ApiError) as error:
        service.commit(identity, staged.import_id, request, "cannot_bypass")
    assert error.value.code == "IMPORT_ERRORS_UNRESOLVED"
    cancel = ImportCancelRequest(expected_input_sha256=staged.input_sha256)
    first = service.cancel(identity, staged.import_id, cancel, "cancel")
    assert service.cancel(identity, staged.import_id, cancel, "cancel") == first
    assert service.cancel(identity, staged.import_id, cancel, "cancel_again") == first
    assert sql_count(database, "objects") == 0
    assert all(service.draft(identity, id).state == "cancelled" for id in preview.preview_refs)
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type='cancelled'", (staged.job.id,)).fetchone()[0] == 1


@pytest.mark.parametrize("fault", ["original", "body", "preview", "draft_revision"])
def test_confirmation_rechecks_raw_blobs_and_exact_preview_snapshot(imports, fault):
    database, service, _, identity = imports
    staged, preview = staged_ready(imports)
    if fault == "original":
        digest = staged.input_sha256
    elif fault == "body":
        block = next(service.draft(identity, id) for id in preview.preview_refs if service.draft(identity, id).kind == "block")
        digest = block.payload.metadata.body_sha256
    elif fault == "preview":
        with database.transaction() as connection:
            raw = json.loads(connection.execute("SELECT preview_json FROM ingestion_imports WHERE id=?", (staged.import_id,)).fetchone()[0])
            next(value for value in raw["objects"] if value["entity"] == "course")["title"] = "Changed without confirmation"
            connection.execute("UPDATE ingestion_imports SET preview_json=? WHERE id=?", (canonical_bytes(raw).decode(), staged.import_id))
        digest = None
    else:
        with database.transaction() as connection:
            connection.execute("UPDATE drafts SET revision=2 WHERE id=?", (preview.preview_refs[0],))
        digest = None
    if digest:
        (database.settings.data_dir / "blobs" / digest[:2] / digest).write_bytes(b"corrupt synthetic bytes")
    with pytest.raises(ApiError):
        service.commit(identity, staged.import_id, decision(staged, preview), "changed")
    assert sql_count(database, "objects") == 0
    assert service.job(identity, staged.job.id).status == "awaiting_approval"


def test_private_download_cancel_and_sources_guard_applies_to_author_during_independent(imports):
    database, service, _, identity = imports
    raw = (FIXTURES / "course-author.learnpack.zip").read_bytes()
    staged, preview = staged_ready(imports, data=raw, filename="author.zip", kind="learnpack")
    block = next(service.draft(author(identity), id) for id in preview.preview_refs if service.draft(author(identity), id).kind == "block")
    source = service.source(author(identity), block.payload.source_id)
    service.commit(author(identity), staged.import_id, decision(staged, preview), "commit")
    with database.transaction() as connection:
        assessment = connection.execute("SELECT id,current_revision FROM objects WHERE kind='assessment'").fetchone()
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES('active_attempt',?,?,?,'independent','{}','[]','[]','active',1,'2026-09-14T00:00:00Z')", (identity.workspace_id, assessment[0], assessment[1]))
    for action in [lambda: service.download(author(identity), source.artifact.artifact_id),
                   lambda: service.source(author(identity), source.id),
                   lambda: service.cancel(author(identity), staged.import_id, ImportCancelRequest(expected_input_sha256=staged.input_sha256), "blocked_cancel"),
                   lambda: service.cancel_job(author(identity), staged.job.id, JobCancelRequest(expected_revision=4), "blocked_job")]:
        with pytest.raises(ApiError) as error:
            action()
        assert error.value.code == "ASSESSMENT_ACTIVE"


def test_concatenated_author_then_learner_zip_remains_private_and_fails_without_partial_preview(imports):
    database, service, worker, identity = imports
    raw = (FIXTURES / "course-author.learnpack.zip").read_bytes() + (FIXTURES / "course-learner.learnpack.zip").read_bytes()
    staged = service.stage(identity, data=raw, filename="mixed.learnpack.zip", kind="learnpack", key="concatenated")
    with database.connect() as connection:
        artifact_id = connection.execute("SELECT id FROM artifacts WHERE profile='import_original'").fetchone()[0]
    assert worker.run_once()
    with pytest.raises(ApiError) as error:
        service.download(identity, artifact_id)
    assert error.value.status == 403
    snapshot = service.job(author(identity), staged.job.id)
    assert snapshot.status == "failed" and snapshot.error.code == "PACKAGE_ENVELOPE_UNCLAIMED"
    assert service.preview(author(identity), staged.import_id).preview_refs == []
    assert sql_count(database, "objects") == sql_count(database, "drafts") == 0


def test_staged_budget_snapshot_survives_smaller_configuration_at_worker_restart_and_commit(tmp_path):
    settings = Settings(data_dir=tmp_path / "budget_data", max_upload_bytes=600000, max_block_characters=500000,
                        max_package_bytes=1000000, max_package_files=80, max_compression_ratio=200)
    database = Database(settings)
    workspace = database.initialize()
    identity = SessionIdentity("budget_session", workspace, "learner", "synthetic", "2099-01-01T00:00:00Z")
    original_service = ImportService(database)
    body = b"x" * 400001
    staged = original_service.stage(identity, data=body, filename="enlarged.txt", kind="text", key="enlarged")
    smaller = replace(settings, max_upload_bytes=200, max_block_characters=100, max_package_bytes=300,
                      max_package_files=2, max_compression_ratio=2)
    restarted_database = Database(smaller)
    worker = ImportWorker(restarted_database)
    assert worker.run_once()
    service = ImportService(restarted_database)
    preview = service.preview(identity, staged.import_id)
    assert preview.status == "preview_ready"
    result = service.commit(identity, staged.import_id, decision(staged, preview), "commit_frozen")
    assert result.course_refs
    block = next(service.draft(identity, id) for id in preview.preview_refs if service.draft(identity, id).kind == "block")
    assert len(block.payload.body_markdown) > 400000 and body.decode() in block.payload.body_markdown
    assert service.content.body(workspace, block.payload.metadata.id, 1)[0] == block.payload.body_markdown.encode()
    source = service.source(identity, block.payload.source_id)
    assert service.download(identity, source.artifact.artifact_id)[0] == body
    with restarted_database.connect() as connection:
        frozen = json.loads(connection.execute("SELECT input_json FROM jobs WHERE id=?", (staged.job.id,)).fetchone()[0])["budgets"]
        assert frozen == {"max_source_bytes": 600000, "max_block_characters": 500000,
                          "max_package_bytes": 1000000, "max_package_files": 80, "max_compression_ratio": 200}


def test_private_pending_cancel_and_failure_are_recoverable_without_private_preview(imports):
    database, service, worker, identity = imports
    raw = (FIXTURES / "course-author.learnpack.zip").read_bytes()
    staged = service.stage(identity, data=raw, filename="author.zip", kind="learnpack", key="cancel_raw")
    request = ImportCancelRequest(expected_input_sha256=staged.input_sha256)
    result = service.cancel(identity, staged.import_id, request, "cancel")
    assert service.cancel(identity, staged.import_id, request, "cancel") == result
    safe = service.preview(identity, staged.import_id)
    assert safe.status == "cancelled" and safe.preview_refs == [] and safe.candidate_summary.block_count == 0
    assert service.job(identity, staged.job.id).status == "cancelled"
    failed = service.stage(identity, data=b"invalid zip", filename="bad.zip", kind="learnpack", key="failed_raw")
    assert worker.run_once()
    safe = service.preview(identity, failed.import_id)
    assert safe.status == "failed" and safe.preview_refs == [] and all(value.locator is None for value in safe.warnings)
    assert service.job(identity, failed.job.id).error.details == []
    with database.connect() as connection:
        artifacts = connection.execute("SELECT id FROM artifacts WHERE profile='import_original'").fetchall()
    for artifact in artifacts:
        with pytest.raises(ApiError) as error:
            service.download(identity, artifact[0])
        assert error.value.status == 403


def test_author_cancelled_private_preview_is_redacted_for_learner_but_retained_for_author(imports):
    database, service, _, identity = imports
    raw = (FIXTURES / "course-author.learnpack.zip").read_bytes()
    staged, preview = staged_ready(imports, data=raw, filename="author.zip", kind="learnpack")
    service.cancel(author(identity), staged.import_id, ImportCancelRequest(expected_input_sha256=staged.input_sha256), "author_cancel")
    learner_preview = service.preview(identity, staged.import_id)
    assert learner_preview.preview_refs == [] and learner_preview.warnings == []
    assert learner_preview.candidate_summary.course_title == "" and learner_preview.candidate_summary.lesson_count == 0
    assert service.job(identity, staged.job.id).warnings == []
    assert service.preview(author(identity), staged.import_id).preview_refs == preview.preview_refs
    with pytest.raises(ApiError):
        service.draft(identity, preview.preview_refs[0])


def test_symbol_course_scope_is_rebound_to_actual_target_course(imports):
    database, service, _, identity = imports
    initial, initial_preview = staged_ready(imports)
    target = service.commit(identity, initial.import_id, decision(initial, initial_preview), "initial").course_refs[0]
    values, bodies = synthetic_tree()
    symbol = dm.Symbol(id="symbol_scope", tex="x", meaning="Synthetic", domain="real", dimension="scalar", scope="course_custom", first_definition=reference(values[0]))
    staged, preview = staged_ready(imports, data=package_bytes(values, bodies, symbols=[symbol]), filename="scope.zip", kind="learnpack", target=target.id, key="scope_stage")
    result = service.commit(identity, staged.import_id, decision(staged, preview), "scope_commit")
    with database.connect() as connection:
        metadata = json.loads(connection.execute("SELECT s.metadata_json FROM sources s JOIN ingestion_imports i ON i.source_id=s.id WHERE i.id=?", (staged.import_id,)).fetchone()[0])
        scope = metadata["symbols"][0]["scope"]
        assert scope == target.id and connection.execute("SELECT 1 FROM objects WHERE id=?", (scope,)).fetchone()
    assert result.course_refs[0].id == scope


def test_expanded_package_budget_accepts_complete_mapping_above_two_thousand_objects(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "large_mapping_data", max_package_files=3000))
    workspace = database.initialize()
    identity = SessionIdentity("session_large_mapping", workspace, "learner", "synthetic", "2099-01-01T00:00:00Z")
    service = ImportService(database)
    worker = ImportWorker(database)
    values, bodies = synthetic_tree()
    concepts = [dm.Concept(id=f"concept_bulk_{number}", revision=1, title=f"Synthetic concept {number}") for number in range(2001)]
    values[-1] = values[-1].model_copy(update={"concept_refs": [reference(value) for value in concepts]})
    originals = [*values, *concepts]
    raw = package_bytes(originals, bodies, budgets=database.settings.import_budgets)
    staged = service.stage(identity, data=raw, filename="large-mapping.learnpack.zip", kind="learnpack", key="large_stage")
    try:
        assert worker.run_once()
        preview = service.preview(identity, staged.import_id)
        assert preview.status == "preview_ready" and len(preview.preview_refs) == 2004
        mappings = [ImportIdMapping(old_id=value.id, new_id=f"mapped_{value.id}") for value in originals]
        request = decision(staged, preview, mappings)
        assert len(request.id_mapping) == 2004
        result = service.commit(identity, staged.import_id, request, "large_commit")
        assert service.commit(identity, staged.import_id, request, "large_commit") == result
        assert len(result.course_refs) == 1 and result.course_refs[0].id == "mapped_course_custom"
        course = service.content.read(workspace, "course", result.course_refs[0].id, 1)
        assert reference(course) == result.course_refs[0]
        assert len(course.concept_refs) == 2001 and all(ref.id.startswith("mapped_concept_bulk_") for ref in course.concept_refs)
        lesson = service.content.read(workspace, "lesson", "mapped_lesson_custom", 1)
        block = service.content.read(workspace, "block", "mapped_block_custom", 1)
        assert lesson.block_refs == [reference(block)]
        assert service.content.body(workspace, block.id, 1) == (bodies[block.body_path], block.body_sha256)
        with database.connect() as connection:
            rows = connection.execute("SELECT o.id,o.kind,o.current_revision,r.revision,r.metadata_json,r.sha256 FROM objects o JOIN revisions r ON r.object_id=o.id WHERE o.workspace_id=?", (workspace,)).fetchall()
            assert len(rows) == 2004
            assert {row["id"] for row in rows} == {value.new_id for value in mappings}
            assert not {row["id"] for row in rows}.intersection(value.id for value in originals)
            stored_refs = {}
            for row in rows:
                model = ENTITY_MODELS[row["kind"]].model_validate_json(row["metadata_json"])
                assert row["revision"] == row["current_revision"] == model.revision == 1
                assert model.id == row["id"] and metadata_sha256(model) == row["sha256"]
                stored_refs[model.id] = reference(model)
            assert all(stored_refs[ref.id] == ref for ref in course.concept_refs + course.lesson_refs)
            assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type IN ('completed','failed','cancelled')", (staged.job.id,)).fetchone()[0] == 1
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        snapshot = service.job(identity, staged.job.id)
        assert snapshot.status == "completed" and snapshot.result_refs == result.course_refs
    finally:
        worker.stop()
