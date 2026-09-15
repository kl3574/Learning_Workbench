from pathlib import Path
import pytest
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_budget import ProofRegistry, RequestPreparer
from services.api.app.provider_dto import FrozenOutboundBudget, ProviderConfigView
from tests.provider_fixture import provider_source
from dataclasses import replace
from packages.contracts.canonical import strict_json
from services.api.app.application.provider_budget import input_bound
from tests.provider_protocol_fixture import MODEL, test_preparer

def test_empty_production_registry_cannot_prepare_or_advertise_chat(tmp_path: Path) -> None:
    db, identity, source, _, job_id = provider_source(tmp_path)
    with db.transaction() as conn:
        material = source.read_prepared(conn, identity, job_id, 1)
    config = ProviderConfigView(id='provider_test', revision=1, config_sha256='a'*64,
        adapter='official_responses', base_url='https://provider.example/v1', model='unregistered-model',
        embedding_model=None, endpoint_policy='public_https', pricing=None, configured=True, secret_present=True)
    budget = FrozenOutboundBudget(max_input_tokens=10000, max_output_tokens=20,
        max_provider_calls=1, max_search_calls=0, max_tool_calls=0, timeout_seconds=180, max_cost_usd=None)
    preparer = RequestPreparer(ProofRegistry())
    with pytest.raises(ApiError) as error:
        preparer.prepare(config, material, budget)
    assert error.value.code == 'CAPABILITY_UNSUPPORTED'
    caps = preparer.capabilities(config, secret_available=True)
    assert caps.configured and not caps.chat and not caps.streaming and not caps.web_search




def prepared_inputs(tmp_path, *, adapter='official_responses'):
    db, identity, source, _, job = provider_source(tmp_path)
    with db.transaction() as conn:
        material = source.read_prepared(conn, identity, job, 1)
    config = ProviderConfigView(id='provider_test', revision=1, config_sha256='a'*64,
        adapter=adapter, base_url='http://127.0.0.1:8765/v1', model=MODEL, embedding_model=None,
        endpoint_policy='explicit_loopback', pricing=None, configured=True, secret_present=True)
    budget = FrozenOutboundBudget(max_input_tokens=20000, max_output_tokens=30,
        max_provider_calls=1, max_search_calls=0, max_tool_calls=0, timeout_seconds=180, max_cost_usd=None)
    return material, config, budget


@pytest.mark.parametrize('adapter', ['official_responses', 'compatible_chat'])
@pytest.mark.parametrize('upper', [False, True])
def test_complete_count_covers_actual_body_not_only_bare_text(tmp_path, adapter, upper):
    material, config, budget = prepared_inputs(tmp_path, adapter=adapter)
    prepared = test_preparer(config.base_url, upper_bound=upper).prepare(config, material, budget)
    assert input_bound(prepared.input_token_assurance) == len(prepared.body) + (10 if upper else 0)
    request = strict_json(prepared.body)
    messages = request['input' if adapter == 'official_responses' else 'messages']
    assert prepared.input_character_count == sum(len(item['content']) for item in messages)
    assert prepared.input_character_count > sum(len(item.content) for item in material.messages)
    assert request['max_output_tokens' if adapter == 'official_responses' else 'max_completion_tokens'] == 30
    assert prepared.cost_estimate.kind == 'unknown'
    assert material.messages[0].content in messages[0]['content']
    assert b'body=' not in repr(prepared).encode()


def test_exact_input_limit_rejects_one_token_over_without_truncation(tmp_path):
    material, config, budget = prepared_inputs(tmp_path)
    preparer = test_preparer(config.base_url)
    original = preparer.prepare(config, material, budget)
    count = input_bound(original.input_token_assurance)
    assert preparer.prepare(config, material, budget.model_copy(update={'max_input_tokens': count})).body == original.body
    with pytest.raises(ApiError) as error:
        preparer.prepare(config, material, budget.model_copy(update={'max_input_tokens': count - 1}))
    assert error.value.code == 'OUTBOUND_BUDGET_EXCEEDED'


@pytest.mark.parametrize('change', ['characters', 'messages', 'blocks', 'output_cap', 'context_cap'])
def test_each_independent_local_shape_or_capacity_limit_is_enforced(tmp_path, change):
    material, config, budget = prepared_inputs(tmp_path)
    preparer = test_preparer(config.base_url)
    if change == 'characters':
        material = material.model_copy(update={'messages': [material.messages[0].model_copy(update={'content': '中' * 12001})]})
    elif change == 'messages':
        material = material.model_copy(update={'messages': material.messages * 7})
    elif change == 'blocks':
        material = material.model_copy(update={'evidence': material.evidence * 9})
    elif change == 'output_cap':
        budget = budget.model_copy(update={'max_output_tokens': 10001})
    else:
        proof = preparer.registry.resolve(config)
        preparer = RequestPreparer(ProofRegistry([replace(proof, shared_context_tokens=100)]))
    with pytest.raises(ApiError) as error:
        preparer.prepare(config, material, budget)
    assert error.value.code == 'OUTBOUND_BUDGET_EXCEEDED'


def test_pricing_proof_hash_is_scoped_to_provider_revision_and_domain(tmp_path):
    from packages.contracts.canonical import canonical_bytes, sha256_bytes
    from services.api.app.provider_dto import ProviderPricing
    material, config, budget = prepared_inputs(tmp_path)
    pricing = ProviderPricing(input_usd_per_million=1.0, output_usd_per_million=2.0, source_note='Synthetic local rate')
    config = config.model_copy(update={'pricing': pricing})
    prepared = test_preparer(config.base_url).prepare(config, material, budget)
    assert prepared.cost_estimate.pricing_sha256 == sha256_bytes(canonical_bytes({
        'version': 'provider-pricing-v1', 'provider_id': config.id,
        'provider_revision': config.revision, 'pricing': pricing.model_dump(mode='json')}))
