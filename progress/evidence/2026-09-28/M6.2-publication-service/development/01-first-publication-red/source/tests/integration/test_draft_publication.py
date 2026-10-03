"""Real Import/Review/SQLite publication; every human decision here is synthetic."""
import pytest

from services.api.app.application.content import ContentService
from services.api.app.application.imports import ImportService
from tests.integration.test_review_workflow import workflow as workflow_fixture
from tests.integration.test_publication_admission import reviewed, publish_request


@pytest.fixture
def workflow(tmp_path):
    yield from workflow_fixture.__wrapped__(tmp_path)


def test_real_pending_import_block_publication_reads_content_without_publishing_parent(workflow):
    from services.api.app.application.draft_publication import DraftPublicationService
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
