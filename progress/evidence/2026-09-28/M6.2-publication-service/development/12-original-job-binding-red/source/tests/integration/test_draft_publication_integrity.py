"""Synthetic damage and current-access changes against real persisted publication."""
import json
from dataclasses import replace

import pytest
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.errors import ApiError
from tests.integration.test_draft_publication import workflow as workflow, ready
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_review_workflow import request, decision
from tests.integration.test_publication_admission import publish_request
from services.api.app.application.imports import ImportService
from services.api.app.application.content import ContentService


def test_rehashed_result_cannot_invent_a_success_without_original_required_warning_ack(workflow):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    service.publish(identity, candidate.draft_id, body, 'published')
    with database.transaction() as conn:
        row = conn.execute('SELECT publication_id,record_json FROM draft_publication_results').fetchone()
        raw = json.loads(row['record_json'])
        raw['request']['acknowledged_warning_codes'] = []
        raw['admission']['acknowledged_warning_codes'] = []
        corrupted = canonical_bytes(raw)
        conn.execute('DROP TRIGGER draft_publication_results_no_update')
        conn.execute('UPDATE draft_publication_results SET record_json=?,sha256=? WHERE publication_id=?',
                     (corrupted.decode(), sha256_bytes(corrupted), row['publication_id']))
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body.model_copy(update={'acknowledged_warning_codes': []}), 'published')
    assert table_hashes(database) == before


@pytest.mark.parametrize('change', ['role', 'revoked', 'expired', 'workspace'])
@pytest.mark.parametrize('replay', [False, True])
def test_current_session_is_revalidated_before_new_or_original_publication(workflow, change, replay):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    if replay:
        service.publish(identity, candidate.draft_id, body, 'published')
    with database.transaction() as conn:
        if change == 'workspace':
            identity = replace(identity, workspace_id='other_synthetic_workspace')
        elif change == 'role':
            conn.execute("UPDATE local_sessions SET role='learner'")
        elif change == 'revoked':
            conn.execute("UPDATE local_sessions SET revoked_at='2000-01-01T00:00:00Z'")
        else:
            conn.execute("UPDATE local_sessions SET expires_at='2000-01-01T00:00:00Z'")
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body, 'published')
    assert table_hashes(database) == before


@pytest.mark.parametrize('mode', ['independent', 'open_book', 'assisted'])
def test_real_current_assessment_policy_blocks_original_ack_but_not_safe_review_job_control(workflow, mode):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture
    database, identity, candidate, reviews, _ = workflow
    service, body, receipt = ready(workflow)
    service.publish(identity, candidate.draft_id, body, 'published')
    fixture = assessment_fixture('publicationpolicy')
    import_fixture(database, identity, fixture, 'policy-material')
    AssessmentService(database).create_attempt(identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'attempt')
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body, 'published')
    assert reviews.read_job(identity, receipt.id).status == 'completed'
    assert table_hashes(database) == before


@pytest.mark.parametrize('damage', ['source_bytes', 'body_bytes', 'report_bytes', 'review_command',
                                  'source_import_membership', 'publication_event', 'publication_actor'])
def test_original_ack_requires_all_physical_and_persistent_evidence(workflow, damage):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    service.publish(identity, candidate.draft_id, body, 'published')
    if damage == 'source_import_membership':
        alternate = ImportService(database).stage(identity, data=b'Synthetic other source.\n',
            filename='other.txt', kind='text', key='other-original').import_id
    with database.transaction() as conn:
        if damage.endswith('_bytes'):
            if damage == 'source_bytes':
                row = conn.execute('SELECT b.relative_path FROM sources s JOIN content_blobs b ON b.sha256=s.blob_sha256').fetchone()
            elif damage == 'body_bytes':
                row = conn.execute('SELECT b.relative_path FROM block_bodies r JOIN content_blobs b ON b.sha256=r.body_sha256').fetchone()
            else:
                row = conn.execute("SELECT b.relative_path FROM artifacts a JOIN content_blobs b ON b.sha256=a.blob_sha256 WHERE a.profile='quality_review_report'").fetchone()
            (database.settings.data_dir / row[0]).write_bytes(b'SYNTHETIC_DAMAGED_PHYSICAL_BYTES')
        elif damage == 'review_command':
            conn.execute('DROP TRIGGER review_commands_no_delete')
            conn.execute('DELETE FROM review_commands')
        elif damage == 'source_import_membership':
            # Break the provenance-owned relation without touching its matching public snapshot/hash.
            conn.execute('DROP TRIGGER block_provenance_no_update')
            conn.execute('UPDATE block_provenance SET import_id=?', (alternate,))
        elif damage == 'publication_event':
            conn.execute('DROP TRIGGER draft_publication_events_no_delete')
            conn.execute('DELETE FROM draft_publication_events WHERE revision=2')
        else:
            conn.execute('DROP TRIGGER draft_publication_commands_no_update')
            conn.execute("UPDATE draft_publication_commands SET route='POST /drafts/another/publish'")
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body, 'published')
    assert table_hashes(database) == before


def test_recursive_review_attachment_is_reverified_after_publication(workflow):
    database, identity, candidate, reviews, worker = workflow
    source = reviews.create(identity, candidate.draft_id, request(candidate), 'evidence-review')
    assert worker.run_once()
    evidence = reviews.read(identity, source.id).evidence_paths[0].split('/')[-2]
    selected = reviews.create(identity, candidate.draft_id, request(candidate), 'selected-review')
    assert worker.run_once()
    original = reviews.read(identity, selected.id)
    receipt = reviews.decide(identity, selected.id,
        decision(original, [evidence], mathematical='NOT_APPLICABLE', sources='APPROVED'), 'selected-human')
    from services.api.app.application.draft_publication import DraftPublicationService
    service = DraftPublicationService(database, reviews, ImportService(database))
    body = publish_request(database, identity, candidate, reviews, receipt)
    service.publish(identity, candidate.draft_id, body, 'published')
    with database.connect() as conn:
        row = conn.execute('SELECT b.relative_path FROM artifacts a JOIN content_blobs b ON b.sha256=a.blob_sha256 WHERE a.id=?',
                           (evidence,)).fetchone()
    (database.settings.data_dir / row[0]).write_bytes(b'SYNTHETIC_DAMAGED_RECURSIVE_REPORT')
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body, 'published')
    assert table_hashes(database) == before


def test_later_real_content_revision_does_not_rebind_original_publication_ack(workflow):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    result = service.publish(identity, candidate.draft_id, body, 'published')
    content = ContentService(database)
    old = content.read(identity.workspace_id, 'block', result.id, 1)
    raw = b'Synthetic later immutable content fixture.\n'
    later = old.model_copy(update={'revision': 2, 'body_path': f'content/{result.id}.r2.md',
                                   'body_sha256': sha256_bytes(raw)})
    later_ref = content.publish(identity.workspace_id, [later], {later.body_path: raw})[0]
    assert later_ref.revision == 2 and later_ref.sha256 != result.sha256
    before = table_hashes(database)
    assert service.publish(identity, candidate.draft_id, body, 'published') == result
    assert content.read(identity.workspace_id, 'block', result.id, 1) == old
    assert table_hashes(database) == before


def test_original_ack_still_checks_the_actual_import_job_input_binding(workflow):
    from tests.integration.test_draft_publication import import_id
    database, identity, candidate, _, _ = workflow
    service, body, receipt = ready(workflow)
    identifier = import_id(workflow, receipt)
    service.publish(identity, candidate.draft_id, body, 'published')
    with database.transaction() as conn:
        conn.execute('UPDATE jobs SET input_sha256=? WHERE id=(SELECT job_id FROM ingestion_imports WHERE id=?)',
                     ('0'*64, identifier))
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body, 'published')
    assert table_hashes(database) == before
