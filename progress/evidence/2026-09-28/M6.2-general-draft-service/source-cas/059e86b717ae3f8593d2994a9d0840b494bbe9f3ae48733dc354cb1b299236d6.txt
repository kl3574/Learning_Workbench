"""Real local edit owner and Quality; human decisions are explicitly synthetic."""
import pytest

from services.api.app.application.content import ContentService
from tests.integration.test_draft_edit_migration import previous as previous
from tests.integration.test_draft_edit_migration import owners
from services.api.app.infrastructure.database import Database


def test_exact_base_copy_and_atomic_whitelisted_edit_preserve_old_content(previous):
    from services.api.app.application.draft_edits import DraftEditService
    from services.api.app.draft_dto import DraftCreateWrite, DraftPatchWrite, DraftPatch
    old, settings, identity, _, _, _, base = previous
    database = Database(settings)
    database.initialize()
    service = DraftEditService(database)
    source = ContentService(database).body(identity.workspace_id, base.id, base.revision)
    created = service.create(identity, DraftCreateWrite(kind='block', base_ref=base, title='Synthetic edited title'), 'create')
    assert created.revision == 1 and created.state == 'draft' and created.base_ref == base
    original = service.read(identity, created.draft_id, 1)
    assert original.payload.body_markdown.encode() == source[0]
    assert original.payload.title == 'Synthetic edited title'
    changed = service.patch(identity, created.draft_id, DraftPatchWrite(expected_revision=1, patches=[
        DraftPatch(field='title', value='Second synthetic title'),
        DraftPatch(field='body_markdown', value='精确正文 🌏\nSecond line.\n')]), 'patch')
    assert changed.revision == 2
    current = service.read(identity, created.draft_id, 2)
    assert current.payload.title == 'Second synthetic title'
    assert current.payload.body_markdown == '精确正文 🌏\nSecond line.\n'
    assert current.candidate != original.candidate and current.base == original.base
    assert service.read(identity, created.draft_id, 1) == original
    assert ContentService(database).body(identity.workspace_id, base.id, base.revision) == source
    assert owners(database)[2].content.current(identity.workspace_id, base.id) == base


def test_real_edit_review_new_head_gate_and_historical_report_survive_patch(previous):
    from services.api.app.application.draft_edits import DraftEditService
    from services.api.app.application.draft_candidates import DraftCandidates
    from services.api.app.application.review_service import ReviewService
    from services.api.app.application.review_numeric import ReviewNumeric
    from services.api.app.application.review_worker import ReviewWorker
    from services.api.app.application.errors import ApiError
    from services.api.app.draft_dto import DraftCreateWrite, DraftPatchWrite, DraftPatch
    from tests.integration.test_review_workflow import request, decision
    _, settings, identity, _, _, _, base = previous
    database = Database(settings)
    database.initialize()
    edits = DraftEditService(database)
    created = edits.create(identity, DraftCreateWrite(kind='block', base_ref=base, title='Synthetic local draft'), 'create')
    record = edits.read(identity, created.draft_id, 1)
    candidates = DraftCandidates({'authoring_edit': edits})
    reviews = ReviewService(database, candidates, ReviewNumeric(candidates, {}), {})
    worker = ReviewWorker(reviews)
    command = request(record.candidate)
    job = reviews.create(identity, created.draft_id, command, 'review')
    edits.patch(identity, created.draft_id, DraftPatchWrite(expected_revision=1,
        patches=[DraftPatch(field='body_markdown', value='Changed synthetic prose.\n')]), 'patch')
    assert worker.run_once()
    receipt = reviews.read(identity, job.id)
    assert receipt.candidate == record.candidate and receipt.structural == 'PASS'
    assert receipt.mathematical == receipt.sources == receipt.independent_pedagogy == 'NOT_RUN'
    approved = reviews.decide(identity, receipt.id, decision(receipt, mathematical='NOT_APPLICABLE', sources='APPROVED'), 'human-synthetic')
    assert approved.reviewer == identity.id
    assert reviews.create(identity, created.draft_id, command, 'review') == job
    assert reviews.read(identity, job.id) == approved
    with pytest.raises(ApiError) as error:
        reviews.create(identity, created.draft_id, command, 'new-stale-review')
    assert error.value.status == 412
    current = edits.read(identity, created.draft_id, 2)
    new_job = reviews.create(identity, created.draft_id, request(current.candidate), 'review-new')
    assert worker.run_once()
    assert reviews.read(identity, new_job.id).mathematical == 'NOT_RUN'
