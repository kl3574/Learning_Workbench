"""Real Import/Review/SQLite publication; every human decision here is synthetic."""
import pytest

from services.api.app.application.content import ContentService
from services.api.app.application.imports import ImportService
from services.api.app.application.errors import ApiError
from services.api.app.application.draft_publication import DraftPublicationService
from services.api.app.infrastructure.publication_repository import PublicationRepository
from services.api.app.import_dto import ImportCancelRequest, ImportCommitRequest, ImportIdMapping
from tests.integration.test_review_workflow import workflow as workflow_fixture
from tests.integration.test_review_workflow import decision
from tests.integration.test_publication_admission import reviewed, publish_request
from tests.integration.test_authoring_numeric_provider_history import table_hashes


@pytest.fixture
def workflow(tmp_path):
    yield from workflow_fixture.__wrapped__(tmp_path)


def ready(workflow, *, review_key='review'):
    database, identity, candidate, reviews, _ = workflow
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE', key=review_key)
    body = publish_request(database, identity, candidate, reviews, receipt)
    return DraftPublicationService(database, reviews, ImportService(database)), body, receipt


def import_id(workflow, receipt):
    database, identity, _, reviews, _ = workflow
    with database.transaction(immediate=False) as conn:
        _, material = reviews.read_publication_basis(conn, identity, receipt.id)
        return material.payload.import_id


def commit_body(imports, identity, identifier, mapping=()):
    preview = imports.preview(identity, identifier)
    return ImportCommitRequest(expected_input_sha256=preview.input_sha256,
        accepted_warning_codes=sorted({w.code for w in preview.warnings}), id_mapping=list(mapping))


def test_real_pending_import_block_publication_reads_content_without_publishing_parent(workflow):
    database, identity, candidate, reviews, _ = workflow
    imports = ImportService(database)
    original = imports.draft(identity, candidate.draft_id)
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt)
    result = DraftPublicationService(database, reviews, imports).publish(identity, candidate.draft_id, body, 'publish')
    content = ContentService(database)
    assert result.entity == 'block' and result.id == original.payload.metadata.id and result.revision == 1
    assert result.sha256 == candidate.candidate_sha256
    assert content.read(identity.workspace_id, 'block', result.id, 1) == original.payload.metadata
    assert content.body(identity.workspace_id, result.id, 1)[0] == original.payload.body_markdown.encode()
    assert imports.draft(identity, candidate.draft_id) == original
    with database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM objects').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM solutions').fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM outbox WHERE event_type='content.published'").fetchone()[0] == 1
    with database.transaction(immediate=False) as conn:
        history = PublicationRepository(conn, identity.workspace_id).for_candidate(candidate)
        assert [e.state for e in history.events] == ['draft', 'in_review', 'approved', 'published']
        assert history.record.result == result and history.record.actor_id == identity.id
        assert history.record.source.source.sha256 == history.record.original_input_sha256
        assert history.record.admission.publication == 'NOT_RUN'
        assert history.record.admission.numeric_check_ids == []


@pytest.mark.parametrize('terminal', ['cancel', 'commit'])
def test_original_publication_ack_survives_real_import_terminal_without_new_publication(workflow, terminal):
    database, identity, candidate, reviews, _ = workflow
    service, body, receipt = ready(workflow)
    imports = ImportService(database)
    identifier = import_id(workflow, receipt)
    result = service.publish(identity, candidate.draft_id, body, 'published')
    if terminal == 'cancel':
        preview = imports.preview(identity, identifier)
        imports.cancel(identity, identifier, ImportCancelRequest(expected_input_sha256=preview.input_sha256), 'cancel')
        assert imports.draft(identity, candidate.draft_id).state == 'cancelled'
    else:
        before = table_hashes(database)
        with pytest.raises(ApiError) as caught:
            imports.commit(identity, identifier, commit_body(imports, identity, identifier), 'unmapped')
        assert caught.value.code == 'IMPORT_ID_COLLISION' and table_hashes(database) == before
        copied_id = 'copy_synthetic_publication_block'
        response = imports.commit(identity, identifier, commit_body(imports, identity, identifier,
            [ImportIdMapping(old_id=result.id, new_id=copied_id)]), 'mapped')
        content = ContentService(database)
        course = content.read(identity.workspace_id, 'course', response.course_refs[0].id, 1)
        lesson = content.read(identity.workspace_id, 'lesson', course.lesson_refs[0].id, 1)
        assert lesson.block_refs[0].id == copied_id and lesson.block_refs[0].sha256 != result.sha256
        assert content.body(identity.workspace_id, copied_id, 1) == content.body(identity.workspace_id, result.id, 1)
        raw, _ = imports.download(identity, response.migration_receipt_id)
        import json
        assert json.loads(raw)['mathematical'] == json.loads(raw)['sources'] == 'NOT_RUN'
        with database.transaction(immediate=False) as conn:
            record = PublicationRepository(conn, identity.workspace_id).for_candidate(candidate).record
            assert record.result == result and record.result != lesson.block_refs[0]
            assert conn.execute('SELECT COUNT(*) FROM draft_publications').fetchone()[0] == 1
    before = table_hashes(database)
    restored = DraftPublicationService(database, reviews, imports)
    assert restored.publish(identity, candidate.draft_id, body, 'published') == result
    with pytest.raises(ApiError):
        restored.publish(identity, candidate.draft_id, body, 'new-key')
    assert table_hashes(database) == before


@pytest.mark.parametrize('terminal', ['cancel', 'commit'])
def test_terminal_import_never_grants_a_new_publication(workflow, terminal):
    database, identity, candidate, _, _ = workflow
    service, body, receipt = ready(workflow)
    imports, identifier = ImportService(database), import_id(workflow, receipt)
    if terminal == 'cancel':
        imports.cancel(identity, identifier,
            ImportCancelRequest(expected_input_sha256=imports.preview(identity, identifier).input_sha256), 'cancel')
    else:
        imports.commit(identity, identifier, commit_body(imports, identity, identifier), 'commit')
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        service.publish(identity, candidate.draft_id, body, 'new')
    assert caught.value.code == 'PUBLICATION_IMPORT_NOT_PENDING' and table_hashes(database) == before


def test_explicit_review_selection_and_later_rejection_do_not_rewrite_original_publication(workflow):
    database, identity, candidate, reviews, _ = workflow
    service, body, accepted = ready(workflow)
    other = reviewed(database, identity, candidate, reviews, key='other', math='NOT_APPLICABLE', sources='REJECTED')
    refused_body = publish_request(database, identity, candidate, reviews, other)
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, refused_body, 'rejected-review')
    assert table_hashes(database) == before
    result = service.publish(identity, candidate.draft_id, body, 'accepted-review')
    current = reviews.decide(identity, accepted.id, decision(accepted, mathematical='REJECTED'), 'later-rejection')
    assert current.revision == 3
    before = table_hashes(database)
    assert service.publish(identity, candidate.draft_id, body, 'accepted-review') == result
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body, 'another-new-key')
    assert table_hashes(database) == before


def test_permanent_commands_survive_generic_idempotency_expiry_and_restart(workflow, monkeypatch):
    from services.api.app.infrastructure import idempotency
    database, identity, candidate, reviews, _ = workflow
    service, body, _ = ready(workflow)
    result = service.publish(identity, candidate.draft_id, body, 'original')
    monkeypatch.setattr(idempotency, 'utc_now', lambda: '2200-01-01T00:00:00Z')
    restored = DraftPublicationService(database, reviews, ImportService(database))
    before = table_hashes(database)
    assert restored.publish(identity, candidate.draft_id, body, 'original') == result
    with pytest.raises(ApiError) as caught:
        restored.publish(identity, candidate.draft_id,
            body.model_copy(update={'acknowledged_warning_codes': []}), 'original')
    assert caught.value.code == 'IDEMPOTENCY_CONFLICT'
    with pytest.raises(ApiError):
        restored.publish(identity, candidate.draft_id, body, 'another')
    assert table_hashes(database) == before
