"""Controlled Provider bytes, real source pins and synthetic numeric execution facts."""
import asyncio

import pytest
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.authoring_numeric_service import NumericService
from services.api.app.application.content import ContentService
from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.draft_publication import DraftPublicationService
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.application.reader import ReaderService
from services.api.app.application.review_numeric import ReviewNumeric
from services.api.app.application.review_service import ReviewService
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.security import expires_after
from services.api.app.provider_dto import ConsentCreate, ConsentPreviewWrite, OutboundBudget
from tests.integration.test_authoring_context import request
from tests.integration.test_authoring_numeric_provider_history import ProviderHistoryCase, table_hashes
from tests.integration.test_authoring_numeric_service import Generated, LedgerRuntime
from tests.integration.test_authoring_provider import configured, payload
from tests.integration.test_publication_admission import publish_request, reviewed, synthetic_numeric
from tests.integration.test_retrieval import publish_small
from tests.provider_protocol_fixture import chat_stream, local_provider


def source_case(tmp_path):
    async def build():
        response = bytearray()
        async with local_provider(payload=response) as server:
            state = configured(tmp_path, server.base_url)
            database, identity, authoring, worker, consents, _ = state
            blocks, lesson, course = publish_small(database, identity, 'source', ['来源甲。\n', '来源乙。\n'])
            refs = [reference(blocks[1]), reference(blocks[0])]
            candidate_payload = payload()
            candidate_payload.update(title=' 标题保留 ', body_markdown='\n原始公式：17+25=42。\n\n',
                                     declared_source_refs=[ref.model_dump() for ref in refs])
            response.extend(chat_stream(canonical_bytes(candidate_payload).decode()))
            job = authoring.prepare(identity, request(refs), 'generation')
            preview = consents.preview(identity, ConsentPreviewWrite(job_id=job.id, expected_job_revision=1,
                provider_id='test_provider', expected_provider_revision=2, expires_at=expires_after(300),
                budget=OutboundBudget(max_input_tokens=20000, max_output_tokens=5000, max_provider_calls=1,
                    max_search_calls=0, max_tool_calls=0, timeout_seconds=10, max_cost_usd=None)), 'consent-preview')
            consents.grant(identity, ConsentCreate(proposal_id=preview.id, proposal_sha256=preview.proposal_sha256), 'consent-grant')
            assert await asyncio.to_thread(worker.run_once)
            candidate = authoring.read(identity, job.id).summary.candidate
            assert candidate is not None and len(server.requests) == 1
            runtime = LedgerRuntime()
            numeric = NumericService(database, authoring.context, runtime, authoring=authoring)
            case = ProviderHistoryCase('single', Generated((database, identity, authoring, numeric, candidate, runtime)))
            catalog = DraftCandidates({'authoring_single': authoring})
            reviews = ReviewService(database, catalog, ReviewNumeric(catalog, {'authoring_single': numeric}), {})
            publication = DraftPublicationService(database, reviews, ImportService(database))
            authoring.verify_publication = publication.verify_recorded
            return case, reviews, publication, refs, lesson, course
    return asyncio.run(build())


@pytest.mark.parametrize('damage_source', [False, True])
def test_exact_dependency_order_no_invented_citations_and_parent_pins_never_change(tmp_path, damage_source):
    case, reviews, publication, refs, lesson, course = source_case(tmp_path)
    original = case.authoring.draft(case.identity, case.candidate.draft_id)
    synthetic_numeric(case, 'synthetic-numeric')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    result = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    content = ContentService(case.database)
    block = content.read(case.identity.workspace_id, 'block', result.id, 1)
    assert block.depends_on == refs and block.citations == block.concepts == []
    assert block.title == original.payload.title == ' 标题保留 '
    assert content.body(case.identity.workspace_id, result.id, 1)[0] == original.payload.body_markdown.encode()
    assert content.read(case.identity.workspace_id, 'lesson', lesson.id, None) == lesson
    assert content.read(case.identity.workspace_id, 'course', course.id, None) == course
    provenance = ReaderService(case.database).block(case.identity, result.id, 1)
    assert provenance.original_source is None and provenance.citations == []
    assert [warning.code for warning in provenance.warnings] == ['PROVENANCE_UNRESOLVED']
    if damage_source:
        with case.database.connect() as conn:
            row = conn.execute('SELECT relative_path FROM content_blobs WHERE sha256=?',
                (content.read(case.identity.workspace_id, 'block', refs[0].id, 1).body_sha256,)).fetchone()
        (case.database.settings.data_dir / row[0]).write_bytes(b'SYNTHETIC_CHANGED_SOURCE_BYTES')
        before = table_hashes(case.database)
        for read in (lambda: case.authoring.draft(case.identity, case.candidate.draft_id),
                     lambda: publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')):
            with pytest.raises(ApiError):
                read()
        assert table_hashes(case.database) == before
