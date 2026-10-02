"""Exact owner history and physical source bytes; no inferred authorizations."""
import json
import sqlite3

import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256, sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.content_draft_source import ContentDraftSource
from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.errors import ApiError
from services.api.app.application.publication_admission import PublicationAdmissionService
from services.api.app.application.publication_admission_models import DraftPublishWrite
from services.api.app.application.review_numeric import ReviewNumeric
from services.api.app.application.review_service import ReviewService
from services.api.app.application.review_worker import ReviewWorker
from services.api.app.draft_dto import DraftCreateWrite, DraftPatch, DraftPatchWrite
from services.api.app.infrastructure.draft_edit_repository import DraftEditRepository
from tests.integration.test_draft_edit_boundaries import case as case, patch
from tests.integration.test_draft_edit_migration import previous as previous, owners
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_review_workflow import request, decision


@pytest.mark.parametrize('fault', ['payload', 'record_hash', 'parent', 'head', 'command', 'base_body', 'provenance'])
def test_bad_original_history_or_physical_base_rejects_reads_and_original_ack(case, fault):
    database, identity, base, service, body, created = case
    original = service.read(identity, created.draft_id, 1)
    service.patch(identity, created.draft_id, patch(), 'patch')
    with database.transaction() as conn:
        if fault in {'payload', 'record_hash', 'parent'}:
            conn.execute('DROP TRIGGER draft_edit_version_no_update')
            if fault == 'payload':
                conn.execute("UPDATE draft_edit_versions SET record_json='{}' WHERE draft_id=? AND revision=1", (created.draft_id,))
            elif fault == 'record_hash':
                conn.execute('UPDATE draft_edit_versions SET record_sha256=? WHERE draft_id=? AND revision=2', ('0' * 64, created.draft_id))
            else:
                # Real FK stays enabled; bind an existing but wrong parent SHA is refused.
                with pytest.raises(sqlite3.IntegrityError):
                    conn.execute('UPDATE draft_edit_versions SET parent_sha256=? WHERE draft_id=? AND revision=2', ('0' * 64, created.draft_id))
                conn.execute("UPDATE draft_edit_versions SET record_json=json_set(record_json,'$.parent_sha256',?) WHERE draft_id=? AND revision=2",
                             ('0' * 64, created.draft_id))
        elif fault == 'head':
            conn.execute('DROP TRIGGER draft_edit_head_transition')
            conn.execute('UPDATE draft_edits SET revision=1 WHERE draft_id=?', (created.draft_id,))
        elif fault == 'command':
            conn.execute('DROP TRIGGER draft_edit_command_no_update')
            conn.execute("UPDATE draft_edit_commands SET record_json='{}' WHERE draft_id=?", (created.draft_id,))
        elif fault == 'provenance':
            conn.execute('DROP TRIGGER block_provenance_no_update')
            conn.execute("UPDATE block_provenance SET snapshot_json='{}' WHERE block_id=?", (base.id,))
        else:
            digest = original.base.metadata.body_sha256
            (database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'Synthetic corrupt physical bytes')
    before = table_hashes(database)
    for call in [lambda: service.read(identity, created.draft_id, 1), lambda: service.create(identity, body, 'create'),
                 lambda: service.patch(identity, created.draft_id, patch(), 'patch')]:
        with pytest.raises(ApiError):
            call()
    assert table_hashes(database) == before


def review(case):
    database, identity, _, service, _, created = case
    candidate = service.read(identity, created.draft_id, 1).candidate
    registry = DraftCandidates({'authoring_edit': service})
    reviews = ReviewService(database, registry, ReviewNumeric(registry, {}), {})
    worker = ReviewWorker(reviews)
    job = reviews.create(identity, created.draft_id, request(candidate), 'review')
    assert worker.run_once()
    receipt = reviews.read(identity, job.id)
    approved = reviews.decide(identity, job.id, decision(receipt, mathematical='NOT_APPLICABLE', sources='APPROVED'), 'synthetic-human')
    return reviews, approved


def test_edited_candidate_never_inherits_old_approval(case):
    database, identity, _, service, _, created = case
    reviews, approved = review(case)
    old = approved.candidate
    original = service.read(identity, created.draft_id, 1)
    body = DraftPublishWrite(expected_revision=1, expected_content_sha256=old.candidate_sha256,
        review_receipt_id=approved.id,
        acknowledged_warning_codes=sorted({w.code for w in original.warnings if w.severity == 'warning'}))
    before = table_hashes(database)
    with database.transaction() as conn:
        admitted = PublicationAdmissionService(reviews).check(conn, identity, created.draft_id, body)
        assert admitted.publication == 'NOT_RUN' and admitted.candidate == old
    assert table_hashes(database) == before
    service.patch(identity, created.draft_id, patch(), 'patch')
    current = service.read(identity, created.draft_id, 2)
    changed = body.model_copy(update={'expected_revision': 2, 'expected_content_sha256': current.candidate.candidate_sha256})
    with database.transaction() as conn:
        with pytest.raises(ApiError) as error:
            PublicationAdmissionService(reviews).check(conn, identity, created.draft_id, changed)
        assert error.value.status == 412
    assert reviews.read(identity, approved.id) == approved


@pytest.mark.parametrize('formula', ['$x^2$', r'\begin{equation*}x=1\end{equation*}'])
def test_actual_edit_mathematics_cannot_be_approved_as_na(case, formula):
    database, identity, _, service, _, created = case
    service.patch(identity, created.draft_id, patch(text=formula), 'math')
    candidate = service.read(identity, created.draft_id, 2).candidate
    registry = DraftCandidates({'authoring_edit': service})
    reviews = ReviewService(database, registry, ReviewNumeric(registry, {}), {})
    job = reviews.create(identity, created.draft_id, request(candidate), 'review')
    assert ReviewWorker(reviews).run_once()
    receipt = reviews.read(identity, job.id)
    with pytest.raises(ApiError) as error:
        reviews.decide(identity, job.id, decision(receipt, mathematical='NOT_APPLICABLE'), 'synthetic-human')
    assert error.value.code == 'MATHEMATICAL_REVIEW_REQUIRED'
    assert reviews.read(identity, job.id).mathematical == 'NOT_RUN'


@pytest.mark.parametrize('formula', ['$x^2$', r'\(x=1\)'])
def test_actual_edit_title_mathematics_with_plain_body_cannot_claim_na(case, formula):
    database, identity, _, service, _, created = case
    service.patch(identity, created.draft_id, DraftPatchWrite(expected_revision=1,
        patches=[DraftPatch(field='title', value=f'Synthetic title {formula}')]), 'math-title')
    current = service.read(identity, created.draft_id, 2)
    assert current.payload.body_markdown == 'Synthetic source for local editing.\n'
    registry = DraftCandidates({'authoring_edit': service})
    reviews = ReviewService(database, registry, ReviewNumeric(registry, {}), {})
    job = reviews.create(identity, created.draft_id, request(current.candidate), 'review-title')
    assert ReviewWorker(reviews).run_once()
    receipt = reviews.read(identity, job.id)
    before = table_hashes(database)
    with pytest.raises(ApiError) as error:
        reviews.decide(identity, job.id, decision(receipt, mathematical='NOT_APPLICABLE'), 'synthetic-human')
    assert error.value.code == 'MATHEMATICAL_REVIEW_REQUIRED'
    assert reviews.read(identity, job.id).mathematical == 'NOT_RUN'
    assert table_hashes(database) == before


def test_edit_na_uses_current_body_while_retaining_exact_historical_formula_base(case):
    database, identity, _, service, _, _ = case
    content = ContentService(database)
    raw = b'Synthetic old formula: \\begin{equation*}x=1\\end{equation*}\n'
    block = dm.ContentBlock(id='synthetic_formula_base', revision=1, kind='text', title='Old $z^2$ formula title',
        body_path='content/synthetic-formula-base.md', body_sha256=sha256_bytes(raw))
    base = content.publish(identity.workspace_id, [block], {block.body_path: raw})[0]
    later = b'Different later published synthetic text.\n'
    content.publish(identity.workspace_id, [block.model_copy(update={'revision': 2, 'body_sha256': sha256_bytes(later)})],
                    {block.body_path: later})
    create_body = DraftCreateWrite(kind='block', base_ref=base, title='Synthetic edited prose')
    created = service.create(identity, create_body, 'formula-base')
    prose = 'Synthetic historical note with no mathematical content.\n'
    service.patch(identity, created.draft_id, patch(text=prose), 'remove-formula')
    current = service.read(identity, created.draft_id, 2)
    assert current.base.ref == base and current.base.body_markdown.encode() == raw
    assert current.base.metadata.title == 'Old $z^2$ formula title'
    assert current.payload.title == 'Synthetic edited prose'
    assert current.payload.body_markdown == prose
    registry = DraftCandidates({'authoring_edit': service})
    reviews = ReviewService(database, registry, ReviewNumeric(registry, {}), {})
    create_review = request(current.candidate)
    job = reviews.create(identity, created.draft_id, create_review, 'prose-review')
    assert ReviewWorker(reviews).run_once()
    machine = reviews.read(identity, job.id)
    assert machine.mathematical == machine.sources == machine.independent_pedagogy == 'NOT_RUN'
    reason = 'Synthetic human fixture: this edited candidate contains historical prose only; no real approval.'
    human = decision(machine, mathematical='NOT_APPLICABLE', reason=reason)
    accepted = reviews.decide(identity, job.id, human, 'synthetic-na-prose')
    assert accepted.mathematical == 'NOT_APPLICABLE' and accepted.sources == 'REJECTED'
    assert accepted.reviewer == identity.id and accepted.decision_reason == reason
    assert accepted.candidate == current.candidate
    assert reviews.read(identity, job.id) == accepted
    artifact_id = machine.evidence_paths[0].split('/')[-2]
    with database.transaction() as conn:
        report, _ = reviews.read_artifact(conn, identity, artifact_id)
    assert json.loads(report)['mathematical'] == 'NOT_RUN'
    # A later edit must neither change this historical judgment nor inherit it.
    service.patch(identity, created.draft_id, patch(2, '$y^2$\n'), 'later-math')
    assert reviews.decide(identity, job.id, human, 'synthetic-na-prose') == accepted
    assert reviews.create(identity, created.draft_id, create_review, 'prose-review') == job
    # Applicability excludes the old base from current-content scanning, but
    # every read/replay still verifies those exact original physical bytes.
    digest = block.body_sha256
    (database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'Synthetic damaged historical base')
    before = table_hashes(database)
    for call in [lambda: service.create(identity, create_body, 'formula-base'),
                 lambda: reviews.read(identity, job.id),
                 lambda: reviews.decide(identity, job.id, human, 'synthetic-na-prose'),
                 lambda: reviews.create(identity, created.draft_id, create_review, 'prose-review')]:
        with pytest.raises(ApiError):
            call()
    assert table_hashes(database) == before


def test_quality_physical_report_remains_checked_for_edit_owner(case):
    database, identity, _, _, _, _ = case
    reviews, receipt = review(case)
    identifier = receipt.evidence_paths[0].split('/')[-2]
    with database.transaction() as conn:
        raw, artifact = reviews.read_artifact(conn, identity, identifier)
    report = json.loads(raw)
    assert [x['status'] for x in report['structure']['checks']] == ['PASS', 'PASS', 'NOT_RUN', 'NOT_RUN']
    assert report['numeric_observation']['checks'] == []
    assert report['numeric_observation']['source_job_id'] is None
    digest = artifact.sha256
    (database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'Synthetic corrupt report')
    with pytest.raises(ApiError):
        reviews.read(identity, receipt.id)


def test_unresolved_sources_are_preserved_without_inventing_origin_or_approval(case):
    database, identity, _, service, _, _ = case
    raw = b'Synthetic public block without retained original.\n'
    block = dm.ContentBlock(id='synthetic_unresolved', revision=1, kind='text', title='Unresolved',
        body_path='content/unresolved.md', body_sha256=sha256_bytes(raw), citations=['synthetic_missing_citation'])
    ref = ContentService(database).publish(identity.workspace_id, [block], {block.body_path: raw})[0]
    created = service.create(identity, DraftCreateWrite(kind='block', base_ref=ref, title='Unresolved copy'), 'unresolved')
    record = service.read(identity, created.draft_id, 1)
    assert record.base.provenance is None and record.payload.citations == ['synthetic_missing_citation']
    assert [x.code for x in record.warnings] == ['PROVENANCE_UNRESOLVED', 'DRAFT_EDIT_UNREVIEWED']


def test_content_source_uses_callers_transaction_and_does_not_require_current_pointer(case):
    database, identity, base, _, _, _ = case
    source = ContentDraftSource(database)
    with database.transaction() as conn:
        original = source.read_exact(conn, identity, base)
        raw = b'Synthetic later version.\n'
        block = original.metadata.model_copy(update={'revision': 2, 'body_sha256': sha256_bytes(raw)})
        ContentService(database).publish_in_transaction(conn, identity.workspace_id, [block], {block.body_path: raw})
        assert source.read_exact(conn, identity, base) == original
        conn.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (identity.id,))
        with pytest.raises(ApiError):
            source.verify_exact(conn, identity, original)


def test_repository_append_fault_is_atomic_even_if_outer_caller_commits(case):
    database, identity, _, service, _, created = case
    original = service.read(identity, created.draft_id, 1)
    # A synthetic proposed r2 uses the actual owner r1; the SQL failure is real.
    from services.api.app.application.draft_edit_models import DraftEditRecord, apply_patch, edit_warnings
    from services.api.app.infrastructure.database import utc_now
    payload = apply_patch(original.payload, patch())
    record = DraftEditRecord(workspace_id=identity.workspace_id, candidate=dm.DraftCandidate(draft_id=created.draft_id,
        draft_revision=2, entity='block', candidate_sha256=metadata_sha256(payload)), base=original.base,
        payload=payload, actor_id=identity.id, command_key='patch', request=patch(), parent_sha256=metadata_sha256(original),
        created_at=utc_now(), warnings=edit_warnings(original.base))
    with database.transaction() as conn:
        conn.execute("CREATE TRIGGER synthetic_append_failure AFTER INSERT ON draft_edit_versions "
                     "BEGIN SELECT RAISE(ABORT,'synthetic append failure'); END")
    before = table_hashes(database)
    with database.transaction() as conn:
        with pytest.raises(sqlite3.Error):
            DraftEditRepository(conn, identity.workspace_id).append(record)
        # Catching the storage error must not leave head r2 without its version.
    assert table_hashes(database) == before
    assert service.read(identity, created.draft_id, 1) == original


@pytest.mark.parametrize('scope', ['kind', 'concept', 'foreign_workspace'])
def test_real_published_bases_outside_first_scope_create_no_edit(case, scope):
    database, identity, base, service, _, _ = case
    content = ContentService(database)
    original = content.read(identity.workspace_id, 'block', base.id, base.revision)
    raw = content.body(identity.workspace_id, base.id, base.revision)[0]
    changes = {'id': 'synthetic_scope', 'citations': []}
    values = []
    workspace = identity.workspace_id
    if scope == 'kind':
        changes['kind'] = 'worked_example'
    elif scope == 'concept':
        concept = dm.Concept(id='synthetic_concept', revision=1, title='Synthetic concept')
        values.append(concept)
        changes['concepts'] = [concept.id]
    else:
        workspace = 'synthetic_other_workspace'
        with database.transaction() as conn:
            conn.execute("INSERT INTO workspace(id,title,created_at) VALUES(?,'Synthetic other','2026-09-28T00:00:00Z')", (workspace,))
    block = dm.ContentBlock.model_validate(original.model_dump() | changes)
    values.append(block)
    ref = content.publish(workspace, values, {block.body_path: raw})[-1]
    before = table_hashes(database)
    with pytest.raises(ApiError) as error:
        service.create(identity, DraftCreateWrite(kind='block', base_ref=ref, title='Synthetic copy'), 'out-of-scope')
    assert error.value.status == (404 if scope == 'foreign_workspace' else 409)
    assert table_hashes(database) == before


def test_edit_review_revalidates_recursive_quality_evidence_bytes(case):
    from services.api.app.application.artifacts import ArtifactsService
    database, identity, _, _, _, _ = case
    reviews, original = review(case)
    other_job = reviews.create(identity, original.candidate.draft_id, request(original.candidate), 'other-review')
    assert ReviewWorker(reviews).run_once()
    other = reviews.read(identity, other_job.id)
    evidence_id = other.evidence_paths[0].split('/')[-2]
    command = decision(original, [evidence_id], mathematical='NOT_APPLICABLE', sources='APPROVED')
    accepted = reviews.decide(identity, original.id, command, 'recursive-human-synthetic')
    assert reviews.read(identity, original.id) == accepted
    with database.transaction() as conn:
        _, artifact = reviews.read_artifact(conn, identity, evidence_id)
    digest = artifact.sha256
    (database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'Synthetic damaged recursive evidence')
    before = table_hashes(database)
    for call in [lambda: reviews.read(identity, original.id),
                 lambda: reviews.decide(identity, original.id, command, 'recursive-human-synthetic'),
                 lambda: ArtifactsService(database, reviews.readers()).download(identity, original.evidence_paths[0].split('/')[-2])]:
        with pytest.raises(ApiError):
            call()
    assert table_hashes(database) == before


def test_edit_storage_rejects_replace_update_and_delete(case):
    database, _, _, _, _, _ = case
    before = table_hashes(database)
    with database.transaction() as conn:
        for table in ['draft_edits', 'draft_edit_versions', 'draft_edit_commands']:
            columns = ','.join(row['name'] for row in conn.execute(f'PRAGMA table_info({table})'))
            for statement in [f'DELETE FROM {table}', f'INSERT OR REPLACE INTO {table}({columns}) SELECT {columns} FROM {table}',
                              f'UPDATE {table} SET ' + ('revision=revision+2' if table == 'draft_edits' else "record_json='{}'")]:
                with pytest.raises(sqlite3.IntegrityError):
                    conn.execute(statement)
    assert table_hashes(database) == before


def test_frozen_origin_descriptor_is_inherited_without_reading_private_original(case):
    """Synthetic private visibility fixture; descriptor inheritance is not source verification."""
    from services.api.app.import_dto import ImportCommitRequest
    from services.api.app.infrastructure.import_worker import ImportWorker
    database, identity, _, service, _, _ = case
    imports = owners(database)[0]
    raw = b'# Synthetic origin\n\nFirst separate paragraph.\n\nSecond separate paragraph.\n'
    staged = imports.stage(identity, data=raw, kind='markdown', filename='origin.md', key='origin')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
    finally:
        worker.stop()
    preview = imports.preview(identity, staged.import_id)
    block = next(item.payload.metadata for item in
        (imports.draft(identity, identifier) for identifier in preview.preview_refs) if item.kind == 'block')
    imports.commit(identity, staged.import_id, ImportCommitRequest(expected_input_sha256=preview.input_sha256,
        accepted_warning_codes=[item.code for item in preview.warnings], id_mapping=[]), 'commit-origin')
    ref = dm.ContentRef(entity='block', id=block.id, revision=block.revision, sha256=metadata_sha256(block))
    assert block.body_sha256 != sha256_bytes(raw)
    digest = sha256_bytes(raw)
    with database.transaction() as conn:
        changed = conn.execute("UPDATE artifacts SET visibility='author_private' WHERE blob_sha256=? AND profile='import_original'", (digest,))
        assert changed.rowcount == 1
    # An actual read of this original would now fail its SHA. Its public parsed
    # body is a different physical blob and is still verified normally.
    (database.settings.data_dir / 'blobs' / digest[:2] / digest).write_bytes(b'Synthetic unreadable private original')
    created = service.create(identity, DraftCreateWrite(kind='block', base_ref=ref, title='Descriptor only'), 'copy-origin')
    record = service.read(identity, created.draft_id, 1)
    assert record.base.provenance.source.sha256 == digest
    assert record.payload.citations == block.citations
    assert record.base.provenance.block_ref == ref
    assert [item.code for item in record.warnings][-1] == 'DRAFT_EDIT_UNREVIEWED'
