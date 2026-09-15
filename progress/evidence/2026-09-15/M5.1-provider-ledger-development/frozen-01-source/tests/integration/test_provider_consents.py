"""Persistent real source owner and a controlled local counting rule; no network."""

from datetime import UTC, datetime, timedelta

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_ports import PreparedProviderRequest
from services.api.app.provider_dto import (
    ConsentCreate, ConsentPreviewWrite, ConsentRevoke, LocalExactInputTokens,
    OutboundBudget, ProviderConfigWrite, ProviderSecretWrite, UnknownCostEstimate,
)
from tests.provider_fixture import provider_source


class ControlledPreparation:
    """Test-only model counts canonical UTF-8 request bytes as tokens by definition."""

    def prepare(self, config, material, budget):
        body = canonical_bytes({'model': config.model, 'messages': [x.model_dump() for x in material.messages],
            'evidence': [x.model_dump() for x in material.evidence], 'max_completion_tokens': budget.max_output_tokens})
        return PreparedProviderRequest(body=body, adapter_version='test-byte-rule-v1',
            input_character_count=sum(len(x.content) for x in material.messages) + sum(len(x.text) for x in material.evidence),
            input_token_assurance=LocalExactInputTokens(kind='local_exact', input_tokens=len(body),
                checker_version='test-byte-rule-v1', proof_sha256=sha256_bytes(b'test-only UTF-8 bytes are tokens'),
                request_body_sha256=sha256_bytes(body)), cost_estimate=UnknownCostEstimate(kind='unknown', currency='USD'))

    def verify(self, config, material, summary, body):
        expected = self.prepare(config, material, summary.budget)
        if body != expected.body or summary.input_token_assurance != expected.input_token_assurance:
            raise ApiError(409, 'CAPABILITY_UNSUPPORTED', '受控测试请求与本机计量规则不匹配。')

    def capabilities(self, config, secret_available):
        return dm.ProviderCapabilities(provider_id=config.id, configured=True, chat=secret_available,
            streaming=secret_available, structured_output=False, web_search=False, tool_calls=False,
            version_evidence='test-only local byte rule; not a production model proof')


def consent_setup(tmp_path):
    from services.api.app.application.providers import ProviderService
    from services.api.app.application.consents import ConsentsService
    from services.api.app.infrastructure.provider_secret_store import FileSecretStore

    database, identity, source, registry, job_id = provider_source(tmp_path)
    store = FileSecretStore(tmp_path / 'provider-secrets')
    store.initialize()
    preparer = ControlledPreparation()
    providers = ProviderService(database, store, preparer)
    providers.save_config(identity, 'provider_test', ProviderConfigWrite(expected_revision=0,
        adapter='compatible_chat', base_url='https://provider.example/v1', model='controlled-byte-model',
        embedding_model=None, endpoint_policy='public_https', pricing=None), 'configure')
    providers.save_secret(identity, 'provider_test', ProviderSecretWrite(expected_revision=1,
        secret='synthetic-controlled-provider-key'), 'secret')
    service = ConsentsService(database, store, registry, preparer)
    request = ConsentPreviewWrite(job_id=job_id, expected_job_revision=1,
        provider_id='provider_test', expected_provider_revision=2,
        budget=OutboundBudget(max_input_tokens=10000, max_output_tokens=100,
            max_provider_calls=1, max_search_calls=0, max_tool_calls=0, max_cost_usd=None),
        expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z'))
    return database, identity, source, service, request


def test_frozen_real_job_grant_revoke_and_original_grant_ack_are_distinct(tmp_path):
    database, identity, source, service, request = consent_setup(tmp_path)
    proposal = service.preview(identity, request, 'preview')
    assert proposal.validity == 'current' and proposal.consent_id is None
    grant_request = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)
    granted = service.grant(identity, grant_request, 'grant-original')
    assert granted.status == 'active' and granted.revision == 1
    lease = source.claim(identity, request.job_id)
    assert lease.job_revision == 2
    revoked = service.revoke(identity, granted.id, ConsentRevoke(expected_revision=1), 'revoke')
    assert revoked.applied and revoked.revision == 2
    assert service.grant(identity, grant_request, 'grant-original') == granted
    current = service.page(identity, consent_id=granted.id).items[0]
    assert current.status == 'revoked' and current.revision == 2 and current.revoked_at is not None
    assert current.summary == proposal.summary
    assert service.proposal(identity, proposal.id).consent_id == granted.id


def test_original_grant_ack_does_not_read_a_later_corrupt_revoke(tmp_path):
    import pytest

    database, identity, _, service, request = consent_setup(tmp_path)
    proposal = service.preview(identity, request, 'preview')
    create = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)
    grant = service.grant(identity, create, 'grant')
    service.revoke(identity, grant.id, ConsentRevoke(expected_revision=1), 'revoke')
    with database.transaction() as conn:
        conn.execute('DROP TRIGGER provider_consent_history_no_update')
        conn.execute("UPDATE provider_consent_history SET history_sha256=? WHERE revision=2", ('0' * 64,))
    assert service.grant(identity, create, 'grant') == grant
    with pytest.raises(ApiError) as error:
        service.page(identity, consent_id=grant.id)
    assert error.value.code == 'PROVIDER_INTEGRITY_INVALID'


def test_grant_and_real_owner_binding_roll_back_together_and_same_command_can_retry(tmp_path):
    import pytest
    from services.api.app.application.provider_ports import OutboundSourceRegistry
    from tests.provider_fixture import PersistedProviderSource, SOURCE_KIND

    database, identity, _, service, request = consent_setup(tmp_path)

    class InterruptedOwner(PersistedProviderSource):
        interrupt = True

        def bind_authorization(self, transaction, actor, job_id, prepared_input_sha256, consent_id):
            super().bind_authorization(transaction, actor, job_id, prepared_input_sha256, consent_id)
            if self.interrupt:
                raise RuntimeError('controlled interruption after real source binding')

    owner = InterruptedOwner(database)
    service.source_registry = OutboundSourceRegistry({SOURCE_KIND: owner})
    proposal = service.preview(identity, request, 'preview')
    create = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)
    with pytest.raises(RuntimeError, match='controlled interruption'):
        service.grant(identity, create, 'grant')
    with database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM provider_consent_history').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM provider_consent_heads').fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM provider_command_history WHERE command_key='grant'").fetchone()[0] == 0
    with pytest.raises(ApiError) as unbound:
        owner.claim(identity, request.job_id)
    assert unbound.value.code == 'CONSENT_REQUIRED'
    owner.interrupt = False
    grant = service.grant(identity, create, 'grant')
    lease = owner.claim(identity, request.job_id)
    assert grant.revision == 1 and lease.job_revision == 2


def test_two_concurrent_approvals_cannot_mint_two_grants_for_one_proposal(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    database, identity, _, service, request = consent_setup(tmp_path)
    proposal = service.preview(identity, request, 'preview')
    create = ConsentCreate(proposal_id=proposal.id, proposal_sha256=proposal.proposal_sha256)

    def approve(key):
        try:
            return service.grant(identity, create, key)
        except ApiError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(approve, ['first-grant', 'second-grant']))
    assert sum(not isinstance(result, ApiError) for result in results) == 1
    assert [result.code for result in results if isinstance(result, ApiError)] == ['CONSENT_ALREADY_GRANTED']
    with database.transaction() as conn:
        assert conn.execute('SELECT COUNT(*) FROM provider_consent_heads').fetchone()[0] == 1


def test_verified_owner_preparation_change_is_stale_but_corrupt_material_is_error(tmp_path):
    import pytest

    database, identity, source, service, request = consent_setup(tmp_path)
    proposal = service.preview(identity, request, 'preview')
    source.advance_preparation(identity, request.job_id)
    with database.transaction() as conn:
        before = sha256_bytes('\n'.join(conn.iterdump()).encode())
    stale = service.proposal(identity, proposal.id)
    assert stale.validity == 'stale' and stale.summary == proposal.summary
    assert any(warning.code == 'source_changed' for warning in stale.warnings)
    with pytest.raises(ApiError) as changed:
        service.grant(identity, ConsentCreate(proposal_id=proposal.id,
            proposal_sha256=proposal.proposal_sha256), 'grant-stale')
    assert changed.value.code == 'OUTBOUND_SOURCE_CHANGED'
    with database.transaction() as conn:
        assert sha256_bytes('\n'.join(conn.iterdump()).encode()) == before
    with database.transaction() as conn:
        conn.execute("UPDATE test_provider_sources SET material_json='{}' WHERE job_id=?", (request.job_id,))
    with pytest.raises(ApiError) as damaged:
        service.proposal(identity, proposal.id)
    assert damaged.value.code == 'OUTBOUND_SOURCE_CHANGED'
