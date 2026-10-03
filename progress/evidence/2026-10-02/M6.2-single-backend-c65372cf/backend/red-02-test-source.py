"""Actual Single/Review/Content owners with explicitly synthetic numeric facts.

The loopback Provider is controlled; LedgerRuntime never executes a process.
These cases establish publication contracts, not physical numeric or content PASS.
"""
import pytest

from services.api.app.application.errors import ApiError
from services.api.app.application.content import ContentService
from services.api.app.application.draft_publication import DraftPublicationService
from services.api.app.application.imports import ImportService
from tests.integration.test_publication_admission import (
    generated_case, publish_request, reviewed, synthetic_numeric,
)
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_authoring_numeric_service import decision


def ready_single(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    service = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = service.verify_recorded
    synthetic_numeric(case, 'synthetic-numeric')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    body = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    return case, reviews, service, body


def test_generated_example_publishes_original_bytes_and_independently_reads_its_exact_ref(tmp_path):
    case, _, publication, intent = ready_single(tmp_path)
    original = case.authoring.draft(case.identity, case.candidate.draft_id)
    generation = case.authoring.read(case.identity, original.source_job_id)
    result = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish-single')
    content = ContentService(case.database)
    block = content.read(case.identity.workspace_id, 'block', result.id, result.revision)
    assert result.entity == 'block' and result.revision == 1
    assert result.id != case.candidate.draft_id and result.sha256 != case.candidate.candidate_sha256
    assert block.kind == 'worked_example' and block.title == original.payload.title
    assert block.concepts == block.citations == block.depends_on == []
    assert content.body(case.identity.workspace_id, result.id, 1)[0] == original.payload.body_markdown.encode()
    current = case.authoring.draft(case.identity, case.candidate.draft_id)
    assert current.state == 'published' and current.published_ref.model_dump() == result.model_dump()
    assert current.payload == original.payload and current.source_job_id == original.source_job_id
    assert case.authoring.read(case.identity, original.source_job_id) == generation
    assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish-single') == result


def test_review_of_old_pass_cannot_publish_after_a_new_numeric_preview(tmp_path):
    case, _, publication, intent = ready_single(tmp_path)
    case.preview('new-preview-after-review')
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        publication.publish(case.identity, case.candidate.draft_id, intent, 'stale-publication')
    assert caught.value.code == 'PUBLISH_NUMERIC_OBSERVATION_STALE'
    assert table_hashes(case.database) == before


def test_publication_blocks_new_preview_and_approval_but_preserves_original_acks(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    publication = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = publication.verify_recorded
    pending = case.preview('pending-before-pass')
    passed = synthetic_numeric(case, 'latest-pass')
    original_approval = case.numeric.decide(case.identity, passed.id, decision(passed), 'latest-pass-approve')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    before = table_hashes(case.database)
    assert case.preview('pending-before-pass') == pending
    assert case.numeric.decide(case.identity, passed.id, decision(passed), 'latest-pass-approve') == original_approval
    for operation in (lambda: case.preview('new-preview'),
                      lambda: case.numeric.decide(case.identity, pending.id, decision(pending), 'new-approval')):
        with pytest.raises(ApiError) as caught:
            operation()
        assert caught.value.code == 'DRAFT_ALREADY_PUBLISHED'
    assert table_hashes(case.database) == before


def test_older_queued_a_cannot_start_after_newer_b_pass_and_publication(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    publication = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = publication.verify_recorded
    first = case.preview('A')
    first_ack = case.numeric.decide(case.identity, first.id, decision(first), 'A-approve')
    synthetic_numeric(case, 'B')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    published = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    # LedgerRuntime has no executor. Any attempted execution is a test failure.
    assert case.worker().run_once()
    current = case.numeric.read(case.identity, first.id)
    assert current.job.id == first_ack.job.id and current.job.status == 'cancelled'
    assert current.result.outcome == 'cancelled' and current.result.started_at is None
    assert current.result.output_sha256 is None
    assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish') == published
    assert case.authoring.draft(case.identity, case.candidate.draft_id).state == 'published'
