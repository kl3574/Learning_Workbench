"""Read-only historical numeric observations from real SQLite owners and loopback generation."""
import pytest

from tests.integration.test_authoring_numeric_provider_history import ProviderHistoryCase, table_hashes
from tests.integration.test_authoring_numeric_service import generated as single_fixture
from tests.integration.test_authoring_group_numeric_service import generated_group


@pytest.fixture(params=['single', 'group'])
def generated(request, tmp_path):
    state = single_fixture.__wrapped__(tmp_path) if request.param == 'single' else generated_group(tmp_path, 'assessment')
    return ProviderHistoryCase(request.param, state)


def test_real_numeric_owner_reads_all_checks_without_writes_or_runtime(generated, monkeypatch):
    case = generated
    first = case.preview('first')
    second = case.preview('second')
    before = table_hashes(case.database)
    with case.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        def forbidden(*args, **kwargs):
            pytest.fail('numeric review must not open another connection or invoke runtime')
        with monkeypatch.context() as patch:
            patch.setattr(case.database, 'connect', forbidden)
            for method in ['prepare', 'check', 'manifest_document', 'run_checked']:
                patch.setattr(case.runtime, method, forbidden, raising=False)
            observation = case.numeric.read_review_numeric(conn, case.identity, case.candidate)
            assert [item.view.id for item in observation.checks] == [first.id, second.id]
            case.numeric.verify_review_numeric(conn, case.identity, observation)
    assert table_hashes(case.database) == before
