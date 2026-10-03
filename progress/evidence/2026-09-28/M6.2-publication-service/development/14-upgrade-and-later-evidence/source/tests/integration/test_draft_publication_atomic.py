"""Real writer serialization and injected SQLite failures, no provider execution."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.infrastructure.publication_repository import PublicationRepository
from services.api.app.infrastructure.database import utc_now
from tests.integration.test_draft_publication import workflow as workflow, ready, import_id, commit_body
from tests.integration.test_authoring_numeric_provider_history import table_hashes


@pytest.mark.parametrize('table,condition', [
    ('revisions', '1'), ('block_provenance', '1'), ('draft_publication_results', '1'),
    ('draft_publication_commands', '1'), ('draft_publication_events', 'NEW.revision=4'),
])
def test_sqlite_failure_rolls_back_content_source_lifecycle_commands_and_outbox(workflow, table, condition):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    with database.transaction() as conn:
        conn.execute(f"CREATE TRIGGER synthetic_publication_failure AFTER INSERT ON {table} WHEN {condition} "
                     "BEGIN SELECT RAISE(ABORT,'synthetic publication failure'); END")
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        service.publish(identity, candidate.draft_id, body, 'published')
    assert caught.value.code == 'PUBLICATION_STORAGE_UNAVAILABLE'
    assert table_hashes(database) == before
    with database.transaction() as conn:
        conn.execute('DROP TRIGGER synthetic_publication_failure')
    assert service.publish(identity, candidate.draft_id, body, 'published').entity == 'block'


@pytest.mark.parametrize('same_key', [False, True])
def test_actual_connections_serialize_competing_publications(workflow, same_key):
    database, identity, candidate, _, _ = workflow
    service, body, _ = ready(workflow)
    barrier = Barrier(2)

    def execute(key):
        barrier.wait(timeout=10)
        try:
            return service.publish(identity, candidate.draft_id, body, key)
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, ['first', 'first' if same_key else 'second']))
    refs = [r for r in results if not isinstance(r, str)]
    assert len(refs) == (2 if same_key else 1)
    assert all(r == refs[0] for r in refs)
    if not same_key:
        assert 'DRAFT_ALREADY_PUBLISHED' in results
    with database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM objects').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM draft_publication_results').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM draft_publication_commands').fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM outbox WHERE event_type='content.published'").fetchone()[0] == 1


def test_actual_import_commit_race_has_only_two_valid_serial_results(workflow):
    database, identity, candidate, _, _ = workflow
    service, body, receipt = ready(workflow)
    imports, identifier = ImportService(database), import_id(workflow, receipt)
    original = commit_body(imports, identity, identifier)
    barrier = Barrier(2)

    def publish():
        barrier.wait(timeout=10)
        try:
            return service.publish(identity, candidate.draft_id, body, 'publish')
        except ApiError as error:
            return error.code

    def commit():
        barrier.wait(timeout=10)
        try:
            return imports.commit(identity, identifier, original, 'commit')
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(publish), pool.submit(commit)
        published, committed = first.result(), second.result()
    if isinstance(published, str):
        assert published == 'PUBLICATION_IMPORT_NOT_PENDING' and not isinstance(committed, str)
        expected, publication_count = 'committed', 0
    else:
        assert committed == 'IMPORT_ID_COLLISION'
        expected, publication_count = 'preview_ready', 1
    assert imports.preview(identity, identifier).status == expected
    with database.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM draft_publications').fetchone()[0] == publication_count


def test_lifecycle_cas_is_separate_from_candidate_revision_and_failed_outer_operation_rolls_back(workflow):
    database, identity, candidate, _, _ = workflow
    before = table_hashes(database)

    class SyntheticOuterRollback(Exception):
        pass

    with pytest.raises(SyntheticOuterRollback):
        with database.transaction() as conn:
            repo = PublicationRepository(conn, identity.workspace_id)
            repo.adopt('publication_synthetic_cas', candidate, utc_now())
            repo.advance('publication_synthetic_cas', 1, 'draft', 'in_review', utc_now())
            with pytest.raises(ApiError) as caught:
                repo.advance('publication_synthetic_cas', candidate.draft_revision, 'in_review', 'approved', utc_now())
            assert caught.value.code == 'PUBLICATION_STATE_CONFLICT'
            assert candidate.draft_revision == 1
            repo.advance('publication_synthetic_cas', 2, 'in_review', 'approved', utc_now())
            raise SyntheticOuterRollback
    assert table_hashes(database) == before


def test_forward_migration_preserves_actual_pending_import_and_review_before_publication(tmp_path):
    from dataclasses import replace
    import shutil
    from packages.contracts import domain_models as dm
    from services.api.app.application.draft_candidates import DraftCandidates
    from services.api.app.application.draft_publication import DraftPublicationService
    from services.api.app.application.imports import IMPORT_ARTIFACT_PROFILES
    from services.api.app.application.review_numeric import ReviewNumeric
    from services.api.app.application.review_service import ReviewService
    from services.api.app.application.sessions import SessionService
    from services.api.app.dto import RoleRequest
    from services.api.app.infrastructure.config import Settings
    from services.api.app.infrastructure.database import Database
    from services.api.app.infrastructure.import_worker import ImportWorker
    from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
    from tests.integration.test_publication_admission import reviewed, publish_request
    settings = Settings(data_dir=tmp_path / 'data')
    previous = tmp_path / 'previous-migrations'
    previous.mkdir()
    for path in settings.migrations_dir.glob('*.sql'):
        if path.name < '0018':
            shutil.copyfile(path, previous / path.name)
    old = Database(replace(settings, migrations_dir=previous))
    old.initialize()
    _, learner = consume_bootstrap(old, issue_bootstrap_code(old))
    SessionService(old).switch_role(learner, RoleRequest(role='author'), 'author')
    identity = replace(learner, role='author')
    imports, worker = ImportService(old), ImportWorker(old)
    try:
        staged = imports.stage(identity, data=b'Synthetic existing content.\n', filename='existing.md', kind='markdown', key='import')
        assert worker.run_once()
    finally:
        worker.stop()
    draft = next(d for d in (imports.draft(identity, identifier) for identifier in
                            imports.preview(identity, staged.import_id).preview_refs) if d.kind == 'block')
    candidate = dm.DraftCandidate(draft_id=draft.id, draft_revision=1, entity='block', candidate_sha256=draft.candidate_sha256)
    owners = DraftCandidates({'import': imports})
    reviews = ReviewService(old, owners, ReviewNumeric(owners, {}), {(p, 'import'): imports for p in IMPORT_ARTIFACT_PROFILES})
    receipt = reviewed(old, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(old, identity, candidate, reviews, receipt)
    before = table_hashes(old)
    upgraded = Database(settings)
    upgraded.initialize()
    after = table_hashes(upgraded)
    assert {k: after[k] for k in before if k != 'schema_migrations'} == {k: v for k, v in before.items() if k != 'schema_migrations'}
    assert list((settings.data_dir / 'backups').glob('*.sqlite3'))
    current_imports = ImportService(upgraded)
    current_owners = DraftCandidates({'import': current_imports})
    current_reviews = ReviewService(upgraded, current_owners, ReviewNumeric(current_owners, {}),
        {(p, 'import'): current_imports for p in IMPORT_ARTIFACT_PROFILES})
    assert current_reviews.read(identity, receipt.id) == receipt
    assert DraftPublicationService(upgraded, current_reviews, current_imports).publish(identity, draft.id, body, 'publish').sha256 == candidate.candidate_sha256
