"""Fault fixtures over real owners; numeric facts are explicitly synthetic."""
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.publication_repository import PublicationRepository
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_single_publication import ready_single


@pytest.mark.parametrize('damage', ['provider', 'body', 'report', 'review_command', 'publication_event',
    'publication_command', 'publication_result', 'binding', 'candidate', 'numeric_output', 'numeric_end_tail',
    'numeric_membership', 'role', 'revoked'])
def test_published_get_and_original_ack_fail_closed_without_writes(tmp_path, damage):
    case, _, publication, intent = ready_single(tmp_path)
    result = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    if damage == 'provider':
        case.damage_original_artifact()
    elif damage == 'publication_result':
        with case.database.connect() as conn:
            conn.execute('PRAGMA foreign_keys=OFF')
            conn.execute('DROP TRIGGER draft_publication_results_no_delete')
            conn.execute('DELETE FROM draft_publication_results')
    else:
        with case.database.transaction() as conn:
            if damage in {'body', 'report'}:
                if damage == 'body':
                    row = conn.execute('SELECT b.relative_path FROM block_bodies r JOIN content_blobs b '
                        'ON b.sha256=r.body_sha256 WHERE r.block_id=?', (result.id,)).fetchone()
                else:
                    row = conn.execute("SELECT b.relative_path FROM artifacts a JOIN content_blobs b "
                        "ON b.sha256=a.blob_sha256 WHERE a.profile='quality_review_report'").fetchone()
                (case.database.settings.data_dir / row[0]).write_bytes(b'SYNTHETIC_CORRUPTED_BYTES')
            elif damage == 'review_command':
                conn.execute('DROP TRIGGER review_commands_no_delete')
                conn.execute('DELETE FROM review_commands')
            elif damage == 'publication_event':
                conn.execute('DROP TRIGGER draft_publication_events_no_delete')
                conn.execute('DELETE FROM draft_publication_events WHERE revision=2')
            elif damage == 'publication_command':
                conn.execute('DROP TRIGGER draft_publication_commands_no_delete')
                conn.execute('DELETE FROM draft_publication_commands')
            elif damage == 'binding':
                conn.execute('DROP TRIGGER single_publication_bindings_no_delete')
                conn.execute('DELETE FROM single_publication_bindings')
            elif damage == 'candidate':
                conn.execute("UPDATE authoring_candidates SET record_sha256=?", ('0'*64,))
            elif damage == 'numeric_output':
                conn.execute("UPDATE authoring_numeric_executions SET end_sha256=?", ('0'*64,))
            elif damage == 'numeric_end_tail':
                conn.execute('UPDATE authoring_numeric_executions SET end_json=NULL,end_sha256=NULL')
            elif damage == 'numeric_membership':
                conn.execute('DELETE FROM authoring_numeric_checks')
            elif damage == 'role':
                conn.execute("UPDATE local_sessions SET role='learner'")
            elif damage == 'revoked':
                conn.execute("UPDATE local_sessions SET revoked_at='2000-01-01T00:00:00Z'")
    before = table_hashes(case.database)
    for read in (lambda: publication.publish(case.identity, case.candidate.draft_id, intent, 'publish'),
                 lambda: case.authoring.draft(case.identity, case.candidate.draft_id)):
        with pytest.raises(ApiError):
            read()
        assert table_hashes(case.database) == before


def test_newer_content_and_later_human_rejection_preserve_original_ref_and_immutable_bytes(tmp_path):
    from tests.integration.test_review_workflow import decision
    case, reviews, publication, intent = ready_single(tmp_path)
    result = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    content = ContentService(case.database)
    block = content.read(case.identity.workspace_id, 'block', result.id, 1)
    raw = b'Synthetic later revision; original published ref stays r1.\n'
    revised = block.model_copy(update={'revision': 2, 'body_path': f'content/{result.id}.r2.md',
                                       'body_sha256': sha256_bytes(raw)})
    assert content.publish(case.identity.workspace_id, [revised], {revised.body_path: raw})[0].revision == 2
    receipt = reviews.read(case.identity, intent.review_receipt_id)
    reviews.decide(case.identity, receipt.id, decision(receipt, mathematical='REJECTED'), 'later-rejection')
    before = table_hashes(case.database)
    assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish') == result
    projected = case.authoring.draft(case.identity, case.candidate.draft_id)
    assert projected.state == 'published' and projected.published_ref.model_dump() == result.model_dump()
    with pytest.raises(ApiError) as caught:
        publication.publish(case.identity, case.candidate.draft_id, intent, 'new-key')
    assert caught.value.code == 'DRAFT_ALREADY_PUBLISHED'
    with pytest.raises(ApiError) as caught:
        publication.publish(case.identity, case.candidate.draft_id,
            intent.model_copy(update={'acknowledged_warning_codes': []}), 'publish')
    assert caught.value.code == 'IDEMPOTENCY_CONFLICT'
    with case.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        history = PublicationRepository(conn, case.identity.workspace_id).single_for_candidate(
            dm.DraftCandidate.model_validate(projected.candidate.model_dump()))
        assert publication.verify_recorded(conn, case.identity, history) == result
    assert table_hashes(case.database) == before
