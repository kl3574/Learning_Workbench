"""Real SQLite owner ledger seams, with a test-only source and input proof."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from services.api.app.application.errors import ApiError
from services.api.app.application.provider_models import CheckedProviderFinished, CheckedProviderError, UsageSnapshot
from services.api.app.infrastructure.consent_repository import ConsentRepository
from services.api.app.infrastructure.database import utc_now
from services.api.app.provider_dto import ConsentCreate, ConsentRevoke
from tests.integration.test_provider_consents import consent_setup


def started_dispatch(tmp_path):
    database, identity, source, service, request = consent_setup(tmp_path)
    proposal = service.preview(identity, request, 'preview')
    grant = service.grant(identity, ConsentCreate(proposal_id=proposal.id,
        proposal_sha256=proposal.proposal_sha256), 'grant')
    lease = source.claim(identity, request.job_id)
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        summary, material, _ = repo.dispatch_material(grant.id)
        source.verify_dispatch(conn, identity, material, lease, grant.id)
        dispatch, created = repo.begin_dispatch(grant.id, request.job_id,
            summary.input_token_assurance.request_body_sha256, utc_now())
        assert created
    return database, identity, service, grant, dispatch


def test_only_first_start_consumes_one_instance_and_restart_retains_unknown(tmp_path):
    database, identity, service, grant, dispatch = started_dispatch(tmp_path)
    service.revoke(identity, grant.id, ConsentRevoke(expected_revision=1), 'revoke')
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        same, created = repo.begin_dispatch(grant.id, dispatch.job_id, dispatch.request_body_sha256, utc_now())
        assert same == dispatch and not created
        assert repo.unfinished_dispatches() == [dispatch]
        with pytest.raises(ApiError) as error:
            repo.check_dispatch(dispatch.id, utc_now())
        assert error.value.code == 'CONSENT_REVOKED'
        assert conn.execute('SELECT COUNT(*) FROM provider_dispatches').fetchone()[0] == 1


@pytest.mark.parametrize('next_usage', [UsageSnapshot(input_tokens=None, output_tokens=3),
    UsageSnapshot(input_tokens=1, output_tokens=3), UsageSnapshot(input_tokens=5, output_tokens=1)])
def test_accepted_usage_cannot_be_erased_or_decreased(tmp_path, next_usage):
    database, identity, _, _, dispatch = started_dispatch(tmp_path)
    first = UsageSnapshot(input_tokens=5, output_tokens=2)
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        repo.record_usage(dispatch.id, first)
        repo.record_usage(dispatch.id, first)
        with pytest.raises(ApiError):
            repo.record_usage(dispatch.id, next_usage)
        assert repo.usage(dispatch.id) == first
        assert conn.execute('SELECT COUNT(*) FROM provider_dispatch_usage').fetchone()[0] == 1


def test_invalid_terminal_never_leaves_partial_ledger_even_if_caller_handles_error(tmp_path):
    database, identity, _, _, dispatch = started_dispatch(tmp_path)
    invalid_relation = CheckedProviderFinished(type='finished', outcome='complete', reason=None,
        output_state='none', usage=UsageSnapshot(input_tokens=5, output_tokens=2))
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        with pytest.raises((ValidationError, ApiError)):
            repo.finish_dispatch(dispatch.id, invalid_relation, b'synthetic answer', b'', utc_now())
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        assert conn.execute('SELECT COUNT(*) FROM provider_artifacts').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM provider_dispatch_usage').fetchone()[0] == 0
        assert repo.read_terminal(dispatch.id) is None


def test_terminal_preceding_actual_start_is_rejected_without_mutation(tmp_path):
    database, identity, _, _, dispatch = started_dispatch(tmp_path)
    terminal = CheckedProviderFinished(type='finished', outcome='complete', reason=None,
        output_state='none', usage=UsageSnapshot(input_tokens=None, output_tokens=None))
    earlier = (datetime.now(UTC) - timedelta(days=1)).isoformat().replace('+00:00', 'Z')
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        with pytest.raises(ApiError):
            repo.finish_dispatch(dispatch.id, terminal, b'', b'', earlier)
        assert repo.read_terminal(dispatch.id) is None


@pytest.mark.parametrize('outcome,channel', [('refused', 'refusal'), ('incomplete', 'answer'), ('error', 'answer')])
def test_terminal_channels_and_unknown_usage_survive_reopen_and_different_terminal_is_rejected(tmp_path, outcome, channel):
    database, identity, service, grant, dispatch = started_dispatch(tmp_path)
    usage = UsageSnapshot(input_tokens=11, output_tokens=None)
    terminal = (CheckedProviderError(type='error', error_code='PROVIDER_OUTCOME_UNKNOWN',
        provider_outcome='unknown', output_state='partial', usage=usage) if outcome == 'error' else
        CheckedProviderFinished(type='finished', outcome=outcome, reason='output_limit' if outcome == 'incomplete' else None,
            output_state='partial' if outcome == 'incomplete' else 'complete', usage=usage))
    answer = b'synthetic partial answer' if channel == 'answer' else b''
    refusal = b'synthetic refusal' if channel == 'refusal' else b''
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        receipt = repo.finish_dispatch(dispatch.id, terminal, answer, refusal, utc_now())
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        assert repo.read_terminal(dispatch.id) == receipt
        assert repo.finish_dispatch(dispatch.id, terminal, answer, refusal, utc_now()) == receipt
        assert repo.unfinished_dispatches() == []
        with pytest.raises(ApiError):
            repo.finish_dispatch(dispatch.id, terminal, b'different bytes', refusal, utc_now())
        assert conn.execute('SELECT COUNT(*) FROM provider_terminals').fetchone()[0] == 1
        assert conn.execute('SELECT bytes FROM provider_artifacts').fetchone()[0] == (answer or refusal)
    view = service.page(identity, consent_id=grant.id).items[0].dispatch
    assert view is not None and view.usage.output_tokens is None
    assert view.error_code == {'refused': 'PROVIDER_REFUSAL', 'incomplete': 'PROVIDER_INCOMPLETE',
                              'error': 'PROVIDER_OUTCOME_UNKNOWN'}[outcome]


def test_reported_usage_with_frozen_known_price_is_estimated_never_provider_billing(tmp_path):
    from services.api.app.provider_dto import ProviderConfigWrite, ProviderPricing

    database, identity, source, service, request = consent_setup(tmp_path)
    original = service._providers.read_config(identity, 'provider_test')
    service._providers.save_config(identity, 'provider_test', ProviderConfigWrite(expected_revision=2,
        **original.model_dump(exclude={'id', 'revision', 'config_sha256', 'configured', 'secret_present', 'pricing'}),
        pricing=ProviderPricing(input_usd_per_million=2, output_usd_per_million=4,
            source_note='Explicit synthetic fixture rates, not a real provider price')), 'priced-config')
    proposal = service.preview(identity, request.model_copy(update={'expected_provider_revision': 3}), 'preview')
    grant = service.grant(identity, ConsentCreate(proposal_id=proposal.id,
        proposal_sha256=proposal.proposal_sha256), 'grant')
    source.claim(identity, request.job_id)
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        dispatch, _ = repo.begin_dispatch(grant.id, request.job_id,
            proposal.summary.input_token_assurance.request_body_sha256, utc_now())
        repo.record_usage(dispatch.id, UsageSnapshot(input_tokens=100, output_tokens=20))
    view = service.page(identity, consent_id=grant.id).items[0].dispatch
    assert view is not None and view.usage.cost.kind == 'estimated'
    assert view.usage.cost.amount == pytest.approx(0.00028)


def test_terminal_storage_failure_rolls_back_usage_and_bytes_inside_caller_transaction(tmp_path):
    import sqlite3

    database, identity, _, _, dispatch = started_dispatch(tmp_path)
    terminal = CheckedProviderFinished(type='finished', outcome='complete', reason=None,
        output_state='complete', usage=UsageSnapshot(input_tokens=5, output_tokens=2))
    with database.transaction() as conn:
        conn.execute("CREATE TRIGGER test_fail_terminal BEFORE INSERT ON provider_terminals BEGIN SELECT RAISE(ABORT,'controlled storage failure'); END")
        with pytest.raises(sqlite3.IntegrityError, match='controlled storage failure'):
            ConsentRepository(conn, identity.workspace_id).finish_dispatch(dispatch.id, terminal, b'synthetic answer', b'', utc_now())
        conn.execute('DROP TRIGGER test_fail_terminal')
    with database.transaction() as conn:
        repo = ConsentRepository(conn, identity.workspace_id)
        assert repo.read_terminal(dispatch.id) is None
        assert repo.usage(dispatch.id) == UsageSnapshot(input_tokens=None, output_tokens=None)
        assert conn.execute('SELECT COUNT(*) FROM provider_artifacts').fetchone()[0] == 0
        receipt = repo.finish_dispatch(dispatch.id, terminal, b'synthetic answer', b'', utc_now())
        assert repo.read_terminal(dispatch.id) == receipt
