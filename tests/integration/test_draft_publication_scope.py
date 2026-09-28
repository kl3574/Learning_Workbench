"""Narrow actual owner eligibility and input privacy; no generated/provider fixtures."""
from dataclasses import replace
import warnings

import pytest
from packages.contracts import domain_models as dm
from services.api.app.application.content import ContentService
from services.api.app.application.draft_publication import DraftPublicationService
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
from tests.integration.test_draft_publication import workflow as workflow, ready, import_id
from tests.integration.test_publication_admission import reviewed, publish_request
from tests.integration.test_authoring_numeric_provider_history import table_hashes


def staged_candidate(workflow, data, kind, filename):
    database, identity, _, _, _ = workflow
    imports, worker = ImportService(database), ImportWorker(database)
    try:
        staged = imports.stage(identity, data=data, kind=kind, filename=filename, key='another-source')
        assert worker.run_once()
        preview = imports.preview(identity, staged.import_id)
        draft = next(d for d in (imports.draft(identity, i) for i in preview.preview_refs) if d.kind == 'block')
        candidate = dm.DraftCandidate(draft_id=draft.id, draft_revision=draft.revision,
                                     entity='block', candidate_sha256=draft.candidate_sha256)
        return imports, draft, candidate
    finally:
        worker.stop()


@pytest.mark.parametrize('kind,filename', [('text', 'synthetic.txt'), ('markdown', 'synthetic.md')])
def test_real_plain_parser_outputs_are_published_exactly_not_raw_upload_normalized(workflow, kind, filename):
    database, identity, _, reviews, _ = workflow
    raw = b'Synthetic plain prose.\n'
    imports, draft, candidate = staged_candidate(workflow, raw, kind, filename)
    receipt = reviewed(database, identity, candidate, reviews, key='plain-review', math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt)
    result = DraftPublicationService(database, reviews, imports).publish(identity, draft.id, body, 'publish')
    actual = ContentService(database).body(identity.workspace_id, result.id, 1)[0]
    assert actual == draft.payload.body_markdown.encode()
    if kind == 'text':
        assert actual != raw and b'```text' in actual


@pytest.mark.parametrize('variant', ['html', 'private_package'])
def test_unsupported_real_parser_owners_cannot_become_published_via_human_enums(workflow, variant):
    database, identity, _, reviews, _ = workflow
    if variant == 'private_package':
        from tests.assessment_fixtures import assessment_fixture
        data, kind, filename = assessment_fixture('publicationprivate').archive, 'learnpack', 'synthetic.learnpack.zip'
    else:
        data, kind, filename = b'<p>Synthetic plain HTML.</p>', 'html', 'synthetic.html'
    imports, draft, candidate = staged_candidate(workflow, data, kind, filename)
    receipt = reviewed(database, identity, candidate, reviews, key='unsupported-review', math='APPROVED')
    body = publish_request(database, identity, candidate, reviews, receipt)
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        DraftPublicationService(database, reviews, imports).publish(identity, draft.id, body, 'publish')
    assert caught.value.code == 'PUBLICATION_OWNER_SCOPE_UNSUPPORTED'
    assert table_hashes(database) == before


@pytest.mark.parametrize('change', ['cancel_requested', 'job_hash', 'job_kind', 'job_workspace'])
def test_jobs_owned_pending_gate_rejects_damaged_or_cancelling_original_job(workflow, change):
    database, identity, candidate, _, _ = workflow
    service, body, receipt = ready(workflow)
    identifier = import_id(workflow, receipt)
    with database.transaction() as conn:
        job = conn.execute('SELECT job_id FROM ingestion_imports WHERE id=?', (identifier,)).fetchone()[0]
        if change == 'cancel_requested':
            conn.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?', (job,))
        elif change == 'job_hash':
            conn.execute('UPDATE jobs SET input_sha256=? WHERE id=?', ('0'*64, job))
        elif change == 'job_kind':
            conn.execute("UPDATE jobs SET kind='draft_review' WHERE id=?", (job,))
        else:
            conn.execute("INSERT INTO workspace(id,title,created_at) SELECT 'other_workspace','Synthetic other',"
                         "created_at FROM workspace LIMIT 1")
            conn.execute("UPDATE jobs SET workspace_id='other_workspace' WHERE id=?", (job,))
    before = table_hashes(database)
    with pytest.raises(ApiError):
        service.publish(identity, candidate.draft_id, body, 'publish')
    assert table_hashes(database) == before


def test_an_already_occupied_original_content_id_is_not_silently_revised(workflow):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    draft = ImportService(database).draft(identity, candidate.draft_id)
    content = ContentService(database)
    content.publish(identity.workspace_id, [draft.payload.metadata],
                    {draft.payload.metadata.body_path: draft.payload.body_markdown.encode()})
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        service.publish(identity, candidate.draft_id, body, 'publish')
    assert caught.value.code == 'PUBLICATION_ID_UNAVAILABLE'
    assert table_hashes(database) == before


def test_same_key_from_a_different_actual_session_is_not_original_actor_replay(workflow):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    result = service.publish(identity, candidate.draft_id, body, 'publish')
    _, learner = consume_bootstrap(database, issue_bootstrap_code(database))
    SessionService(database).switch_role(learner, RoleRequest(role='author'), 'second-author')
    other = replace(learner, role='author')
    assert other.id != identity.id
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        service.publish(other, candidate.draft_id, body, 'publish')
    assert caught.value.code == 'DRAFT_ALREADY_PUBLISHED'
    assert service.publish(identity, candidate.draft_id, body, 'publish') == result
    assert table_hashes(database) == before


def test_invalid_model_construct_input_emits_no_private_serializer_warning(workflow):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    forged = body.model_copy(update={'acknowledged_warning_codes': [{'private': 'synthetic-secret-marker'}]})
    before = table_hashes(database)
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter('always')
        with pytest.raises(ApiError) as caught:
            service.publish(identity, candidate.draft_id, forged, 'publish')
    assert observed == [] and 'synthetic-secret-marker' not in str(caught.value)
    assert table_hashes(database) == before
