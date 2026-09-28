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
