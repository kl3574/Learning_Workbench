"""Original Tutor command replay must retain the actual owned conversation."""

import pytest

from services.api.app.application.errors import ApiError
from tests.integration.test_retrieval import all_rows
from tests.integration.test_tutor_runs import started, tutor as tutor_fixture


@pytest.mark.parametrize('command', ['thread', 'run'])
def test_original_ack_replay_rejects_missing_owned_user_message(tmp_path, command):
    database, identity, service, create = values = tutor_fixture.__wrapped__(tmp_path)
    _, request, ack = started(values)
    with database.transaction() as conn:
        conn.execute('DELETE FROM tutor_messages WHERE message_id IN (SELECT id FROM messages WHERE run_id=?)', (ack.run.id,))
        conn.execute('DELETE FROM messages WHERE run_id=?', (ack.run.id,))
    before = all_rows(database)
    with pytest.raises(ApiError) as corrupt:
        if command == 'thread':
            service.create_thread(identity, create, 'thread')
        else:
            service.start(identity, request, 'start')
    assert corrupt.value.code == 'TUTOR_INTEGRITY_ERROR'
    assert all_rows(database) == before
