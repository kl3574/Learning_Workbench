"""Actual pre-0025 Restore v1 publication/Review bytes remain historically readable."""
from dataclasses import replace
import shutil
import sqlite3
import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.content_restore import ContentRestoreService
from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.draft_publication import DraftPublicationService
from services.api.app.application.imports import ImportService
from services.api.app.application.review_numeric import ReviewNumeric
from services.api.app.application.review_service import ReviewService
from services.api.app.application.sessions import SessionService
from services.api.app.content_restore_dto import ContentRestoreDraftCreateWrite
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
from tests.integration.test_publication_admission import reviewed, publish_request
from tests.integration.test_authoring_numeric_provider_history import table_hashes


@pytest.fixture
def legacy(tmp_path):
    settings = Settings(data_dir=tmp_path / 'data')
    prior = tmp_path / 'migrations'
    prior.mkdir()
    for path in settings.migrations_dir.glob('*.sql'):
        if path.name < '0025':
            shutil.copyfile(path, prior / path.name)
    old = Database(replace(settings, migrations_dir=prior))
    old.initialize()
    _, learner = consume_bootstrap(old, issue_bootstrap_code(old))
    SessionService(old).switch_role(learner, RoleRequest(role='author'), 'author')
    identity = replace(learner, role='author')
    content = ContentService(old)
    body = b'Synthetic old theorem; no numeric pipeline or real academic approval.\n'
    block = dm.ContentBlock(id='legacy_restore', revision=1, kind='theorem', title='Old theorem',
        body_path='content/legacy_restore.md', body_sha256=sha256_bytes(body), concepts=[], citations=[], depends_on=[])
    source = content.publish(identity.workspace_id, [block], {block.body_path: body})[0]
    base = content.publish(identity.workspace_id, [block.model_copy(update={'revision': 2})], {block.body_path: body})[0]
    restores = ContentRestoreService(old)
    candidate = restores.create(identity, ContentRestoreDraftCreateWrite(source_ref=source, expected_current_ref=base,
        reason='Synthetic prior Restore intent.'), 'restore').candidate
    candidates = DraftCandidates({'authoring_restore': restores})
    reviews = ReviewService(old, candidates, ReviewNumeric(candidates, {}), {})
    receipt = reviewed(old, identity, candidate, reviews)
    body = publish_request(old, identity, candidate, reviews, receipt)
    publication = DraftPublicationService(old, reviews, ImportService(old))
    ref = publication.publish(identity, candidate.draft_id, body, 'publish')
    return old, settings, identity, candidate, receipt, body, ref


def test_numeric_migration_preserves_actual_old_restore_review_and_publication(legacy):
    old, settings, identity, candidate, receipt, body, ref = legacy
    before = table_hashes(old)
    with old.connect() as conn:
        original = {table: [tuple(row) for row in conn.execute(f'SELECT rowid,* FROM {table} ORDER BY rowid')]
                    for table in ['content_restore_drafts', 'content_restore_commands', 'review_revisions', 'draft_publication_results']}
        assert any('review-numeric-observation-v1' in str(value) for value in original['review_revisions'][0])
    upgraded = Database(settings)
    upgraded.initialize()
    after = table_hashes(upgraded)
    assert {k: after[k] for k in before if k != 'schema_migrations'} == {k: v for k, v in before.items() if k != 'schema_migrations'}
    with upgraded.connect() as conn:
        assert {table: [tuple(row) for row in conn.execute(f'SELECT rowid,* FROM {table} ORDER BY rowid')]
                for table in original} == original
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    from services.api.app.main import create_app
    app = create_app(settings)
    assert app.state.review_service.read(identity, receipt.id) == receipt
    assert app.state.publication_service.publish(identity, candidate.draft_id, body, 'publish') == ref
    snapshot = app.state.content_restore_service.read(identity, candidate.draft_id)
    assert snapshot.state == 'published' and snapshot.numeric_material is None and snapshot.numeric_check_ids == []
    assert table_hashes(upgraded) == after


def test_numeric_migration_failure_is_atomic_with_old_real_history(legacy):
    old, settings, *_ = legacy
    text = (settings.migrations_dir / '0025_restore_numeric.sql').read_text()
    (old.settings.migrations_dir / '0025_restore_numeric.sql').write_text(text + '\nSELECT synthetic_restore_numeric_failure();\n')
    before = table_hashes(old)
    with old.connect() as conn:
        schema = [tuple(row) for row in conn.execute('SELECT * FROM sqlite_master ORDER BY type,name')]
    with pytest.raises(sqlite3.Error):
        old.initialize()
    assert table_hashes(old) == before
    with old.connect() as conn:
        assert [tuple(row) for row in conn.execute('SELECT * FROM sqlite_master ORDER BY type,name')] == schema
