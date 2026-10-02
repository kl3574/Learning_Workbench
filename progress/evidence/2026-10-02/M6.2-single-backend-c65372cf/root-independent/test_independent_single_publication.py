"""Independent bounded owner probes; numeric ledger is synthetic, never physical PASS."""
from contextlib import contextmanager
import pytest
from services.api.app.application.draft_publication import DraftPublicationService
from services.api.app.application.imports import ImportService
from services.api.app.application.errors import ApiError
from tests.integration.test_single_publication import ready_single
from tests.integration.test_publication_admission import generated_case, reviewed, publish_request, synthetic_numeric
from tests.integration.test_authoring_numeric_service import decision
from tests.integration.test_authoring_numeric_provider_history import table_hashes


def test_published_projection_works_under_sqlite_query_only_not_merely_equal_final_rows(tmp_path, monkeypatch):
    case, _, service, intent = ready_single(tmp_path)
    published = service.publish(case.identity, case.candidate.draft_id, intent, 'publication')
    before = table_hashes(case.database)
    connect = case.database.connect
    @contextmanager
    def readonly(**kwargs):
        with connect(**kwargs) as conn:
            conn.execute('PRAGMA query_only=ON')
            yield conn
    monkeypatch.setattr(case.database, 'connect', readonly)
    actual = case.authoring.draft(case.identity, case.candidate.draft_id)
    assert actual.published_ref.model_dump() == published.model_dump()
    assert table_hashes(case.database) == before


def test_unavailable_publication_verifier_must_not_hide_published_record_as_draft(tmp_path):
    case, _, service, intent = ready_single(tmp_path)
    service.publish(case.identity, case.candidate.draft_id, intent, 'publication')
    case.authoring.verify_publication = None
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        case.authoring.draft(case.identity, case.candidate.draft_id)
    assert (caught.value.status, caught.value.code) == (503, 'PUBLICATION_OWNER_UNAVAILABLE')
    assert table_hashes(case.database) == before


def test_declining_older_pending_check_changes_review_endpoint_even_when_latest_pass_unchanged(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    service = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = service.verify_recorded
    older = case.preview('older-pending')
    latest = synthetic_numeric(case, 'latest')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    case.numeric.decide(case.identity, older.id, decision(older, action='decline'), 'later-decline')
    assert case.numeric.read(case.identity, latest.id).result.verdict == 'PASS'
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        service.publish(case.identity, case.candidate.draft_id, intent, 'old-review')
    assert caught.value.code == 'PUBLISH_NUMERIC_OBSERVATION_STALE'
    assert table_hashes(case.database) == before


def test_post_publication_allowed_decline_keeps_actual_result_and_original_publication_ack(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    service = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = service.verify_recorded
    older = case.preview('older-pending')
    latest = synthetic_numeric(case, 'latest')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    published = service.publish(case.identity, case.candidate.draft_id, intent, 'publication')
    actual = case.numeric.read(case.identity, latest.id)
    declined = case.numeric.decide(case.identity, older.id, decision(older, action='decline'), 'late-decline')
    assert declined.job is None
    before = table_hashes(case.database)
    assert case.numeric.read(case.identity, latest.id) == actual
    assert service.publish(case.identity, case.candidate.draft_id, intent, 'publication') == published
    assert case.authoring.draft(case.identity, case.candidate.draft_id).published_ref.model_dump() == published.model_dump()
    assert table_hashes(case.database) == before
