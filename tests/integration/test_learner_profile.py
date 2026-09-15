"""Actual SQLite profile history, CAS, replay, migration and HTTP provenance."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.profile import ProfileService
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database, utc_now
from services.api.app.infrastructure.profile_repository import PROFILE_ROUTE
from services.api.app.infrastructure.security import SessionIdentity, issue_bootstrap_code
from services.api.app.main import create_app
from services.api.app.profile_dto import ProfileWrite, SelfAssessmentWrite
from tests.integration.test_assessment_attempts import import_fixture, start, storage as assessment_storage
from tests.assessment_fixtures import assessment_fixture


@pytest.fixture
def profile_store(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'profile'))
    workspace = database.initialize()
    identity = SessionIdentity('session_profile', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    return database, identity, ProfileService(database)


def request(revision=1, **changes):
    data = dict(expected_revision=revision, goals=['Original synthetic goal'], goal_concept_ids=[], weekly_minutes=120,
                language='zh-CN', preferred_difficulty='beginner', self_assessments=[])
    data.update(changes)
    return ProfileWrite.model_validate(data)


def profile_rows(database):
    with database.connect() as connection:
        return {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in ('learner_profiles', 'learner_profile_history', 'learner_profile_command_receipts',
                          'learner_profile_legacy_snapshots', 'learning_events', 'evidence', 'idempotency')}


def test_empty_get_has_no_storage_effect_and_first_put_is_revision_two(profile_store):
    database, identity, service = profile_store
    before = profile_rows(database)
    assert service.read(identity.workspace_id) == dm.LearnerProfile(workspace_id=identity.workspace_id, revision=1)
    assert profile_rows(database) == before
    saved = service.save(identity, request(), 'profile-first')
    assert saved.revision == 2 and service.read(identity.workspace_id) == saved
    after = profile_rows(database)
    assert len(after['learner_profile_history']) == len(after['learner_profile_command_receipts']) == 1
    assert after['learning_events'] == before['learning_events'] and after['evidence'] == before['evidence']


def test_parallel_expected_revision_yields_one_success_one_412_and_real_get(profile_store):
    _, identity, service = profile_store
    def save(index):
        try:
            return service.save(identity, request(goals=[f'Goal {index}']), f'race-{index}')
        except ApiError as error:
            return error
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(save, [1, 2]))
    successes = [value for value in values if isinstance(value, dm.LearnerProfile)]
    errors = [value for value in values if isinstance(value, ApiError)]
    assert len(successes) == len(errors) == 1 and errors[0].status == 412
    assert service.read(identity.workspace_id) == successes[0]


def test_old_replay_keeps_original_revision_and_expired_key_can_allocate_new_revision(profile_store):
    database, identity, service = profile_store
    first = service.save(identity, request(), 'same-key')
    second = service.save(identity, request(2, goals=['Second goal']), 'second')
    before = profile_rows(database)
    assert service.save(identity, request(), 'same-key') == first and profile_rows(database) == before
    assert service.read(identity.workspace_id) == second
    with database.transaction() as connection:
        connection.execute("UPDATE idempotency SET expires_at='2000-01-01T00:00:00Z' WHERE route=? AND key='same-key'", (PROFILE_ROUTE,))
    third = service.save(identity, request(3), 'same-key')
    assert third.revision == 4
    assert len(profile_rows(database)['learner_profile_history']) == 3


@pytest.mark.parametrize('corruption', ['retarget', 'bad_json_shape', 'current_hash', 'receipt_missing'])
def test_bad_current_or_cached_receipt_is_never_a_success(profile_store, corruption):
    database, identity, service = profile_store
    service.save(identity, request(), 'first')
    later = service.save(identity, request(2), 'second')
    with database.transaction() as connection:
        if corruption in {'retarget', 'bad_json_shape'}:
            result = later.model_dump_json() if corruption == 'retarget' else '[]'
            connection.execute("UPDATE idempotency SET result_json=? WHERE route=? AND key='first'", (result, PROFILE_ROUTE))
        elif corruption == 'current_hash':
            payload = later.model_dump(mode='json')
            payload['goals'] = ['Altered cache']
            connection.execute('UPDATE learner_profiles SET profile_json=? WHERE workspace_id=?', (json.dumps(payload), identity.workspace_id))
        else:
            connection.execute("DELETE FROM learner_profile_command_receipts WHERE key='first'")
    before = profile_rows(database)
    with pytest.raises(ApiError) as rejected:
        service.save(identity, request(), 'first')
    assert rejected.value.code == 'PROFILE_INTEGRITY_INVALID' and profile_rows(database) == before


def test_history_and_receipt_failure_roll_back_entire_first_put(profile_store):
    database, identity, service = profile_store
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_receipt_failure BEFORE INSERT ON learner_profile_command_receipts BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    before = profile_rows(database)
    with pytest.raises(ApiError) as rejected:
        service.save(identity, request(), 'retry')
    assert rejected.value.code == 'PROFILE_STORAGE_UNAVAILABLE' and profile_rows(database) == before
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER injected_receipt_failure')
    assert service.save(identity, request(), 'retry').revision == 2
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute('UPDATE learner_profile_history SET updated_at=?', (utc_now(),))


def test_server_self_report_time_and_identity_validation_never_mutate_evidence(profile_store):
    database, identity, service = profile_store
    fixture = assessment_fixture('profile')
    import_fixture(database, identity, fixture, 'profile-content')
    first = service.save(identity, request(goal_concept_ids=[fixture.concept.id],
        self_assessments=[SelfAssessmentWrite(concept_id=fixture.concept.id, level='independent_use').model_dump()]), 'self')
    assert first.self_assessments[0].origin == 'self_report'
    assert first.self_assessments[0].updated_at.endswith('Z')
    before = profile_rows(database)
    second = service.save(identity, request(2, goals=['Only goal changed'], goal_concept_ids=[fixture.concept.id],
        self_assessments=[{'concept_id': fixture.concept.id, 'level': 'independent_use'}]), 'goal')
    assert second.self_assessments == first.self_assessments
    after = profile_rows(database)
    assert after['evidence'] == before['evidence'] and after['learning_events'] == before['learning_events']
    with pytest.raises(ApiError) as rejected:
        service.save(identity, request(3, goal_concept_ids=['concept_missing']), 'unknown')
    assert rejected.value.code == 'PROFILE_CONCEPT_UNAVAILABLE'


@pytest.mark.parametrize('bad', [
    {'revision': 1}, {'workspace_id': 'workspace_spoof'}, {'weekly_minutes': True},
    {'goal_concept_ids': ['concept_a', 'concept_a']},
    {'self_assessments': [{'concept_id': 'concept_a', 'level': 'not_learned', 'origin': 'native'}]},
    {'self_assessments': [{'concept_id': 'concept_a', 'level': 'not_learned', 'updated_at': '2026-01-01T00:00:00Z'}]},
    {'self_assessments': [{'concept_id': 'concept_a', 'level': 'not_learned'}] * 2},
])
def test_strict_request_rejects_client_provenance_and_ambiguous_identities(bad):
    with pytest.raises(ValidationError):
        ProfileWrite.model_validate({**request().model_dump(), **bad})


def test_current_independent_guard_precedes_successful_replay_and_workspace_isolation(tmp_path):
    storage = assessment_storage.__wrapped__(tmp_path)
    database, identity, _, _ = storage
    service = ProfileService(database)
    service.save(identity, request(), 'before-test')
    start(storage)
    before = profile_rows(database)
    for call in [lambda: service.read(identity.workspace_id), lambda: service.save(identity, request(), 'before-test')]:
        with pytest.raises(ApiError) as rejected:
            call()
        assert rejected.value.status == 409 and rejected.value.code != 'PROFILE_INTEGRITY_INVALID'
    assert profile_rows(database) == before
    with database.transaction() as connection:
        connection.execute('INSERT INTO workspace(id,title,preferences_json,created_at) VALUES(?,?,?,?)',
            ('workspace_other', 'Synthetic other workspace', '{}', utc_now()))
    other = replace(identity, workspace_id='workspace_other')
    assert service.save(other, request(), 'before-test').workspace_id == other.workspace_id


@pytest.mark.parametrize('bad_time', [False, True])
def test_legacy_profile_bytes_and_time_are_preserved_or_explicitly_rejected(tmp_path, bad_time):
    directory = tmp_path / 'legacy_migrations'
    directory.mkdir()
    migration_root = Path('migrations')
    for path in migration_root.glob('*.sql'):
        if path.name < '0008':
            shutil.copyfile(path, directory / path.name)
    database = Database(Settings(data_dir=tmp_path / 'legacy', migrations_dir=directory))
    workspace = database.initialize()
    profile = dm.LearnerProfile(workspace_id=workspace, revision=7, goals=['Legacy original goal'])
    raw = json.dumps(profile.model_dump(), indent=3, ensure_ascii=False)
    timestamp = 'unparseable' if bad_time else '2026-09-14T00:00:00Z'
    with database.transaction() as connection:
        connection.execute('INSERT INTO learner_profiles VALUES(?,?,?,?)', (workspace, 7, raw, timestamp))
    shutil.copyfile(migration_root / '0008_learner_profile_history.sql', directory / '0008_learner_profile_history.sql')
    database.initialize()
    service = ProfileService(database)
    before = profile_rows(database)
    if bad_time:
        with pytest.raises(ApiError) as rejected:
            service.read(workspace)
        assert rejected.value.code == 'PROFILE_INTEGRITY_INVALID' and profile_rows(database) == before
        return
    assert service.read(workspace) == profile and profile_rows(database) == before
    identity = SessionIdentity('session_legacy', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    assert service.save(identity, request(7), 'migrated').revision == 8
    with database.connect() as connection:
        stored = connection.execute('SELECT * FROM learner_profile_history WHERE revision=7').fetchone()
    assert stored['profile_json'] == raw and stored['updated_at'] == timestamp
    assert stored['profile_sha256'] == sha256_bytes(raw.encode()) and stored['record_kind'] == 'legacy_preserved'


def test_actual_http_rejects_repeated_unknown_fields_and_requires_csrf(profile_store):
    database, _, _ = profile_store
    app = create_app(database.settings)
    with TestClient(app) as client:
        client.base_url = database.settings.origin
        code = issue_bootstrap_code(database)
        boot = client.post('/api/v1/session/bootstrap', json={'one_time_code': code}, headers={'Origin': database.settings.origin})
        assert boot.status_code == 200
        headers = {'Origin': database.settings.origin, 'X-CSRF-Token': boot.json()['csrf_token'], 'Idempotency-Key': 'http-profile'}
        response = client.get('/api/v1/learner/profile')
        assert response.status_code == 200 and response.json()['revision'] == 1
        assert response.headers['Cache-Control'] == 'no-store'
        assert client.get('/api/v1/learner/profile?revision=1').status_code == 422
        assert client.put('/api/v1/learner/profile', json=request().model_dump()).status_code == 403
        assert client.put('/api/v1/learner/profile', json=request().model_dump(), headers=headers).status_code == 200
        repeated = list(headers.items()) + [('Idempotency-Key', 'duplicate')]
        assert client.put('/api/v1/learner/profile', json=request().model_dump(), headers=repeated).status_code == 422
