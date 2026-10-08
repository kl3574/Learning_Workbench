"""Synthetic complete-request proof checks; no runtime, sockets or model calls."""
from dataclasses import replace
import base64

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_budget import ProofRegistry
from services.api.app.codex_turn_dto import CodexLocalToolBudget, CodexOutboundBudgetWrite
from services.api.app.provider_dto import ProviderConfigView


BOOTSTRAP = 'a' * 64


def tools():
    return CodexLocalToolBudget(max_tool_calls=2, wall_seconds=30)


def config(**changes):
    value = dict(id='provider_peer', revision=2, config_sha256='b' * 64,
        adapter='official_responses', base_url='http://127.0.0.1:4321/synthetic',
        model='synthetic-byte-token-model-v1', embedding_model=None,
        endpoint_policy='explicit_loopback', pricing=None, configured=True, secret_present=True)
    return ProviderConfigView(**(value | changes))


def budget(**changes):
    value = dict(max_input_tokens=500000, max_output_tokens=100,
        max_provider_calls=1, max_search_calls=0, max_cost_usd=None)
    return CodexOutboundBudgetWrite(**(value | changes))


def messages(text='Explain 完整输入 😀 e\u0301'):
    return [dm.GenerationMessage(role='system', content='Only the frozen inputs.'),
        dm.GenerationMessage(role='user', content=text)]


def proof(**changes):
    from services.api.app.application.provider_codex_profile import SyntheticCodexProof
    values = dict(registration_id='controlled_peer', config=config(), bootstrap_sha256=BOOTSTRAP,
        model_versions=['synthetic-byte-token-model-v1'], kind='local_exact',
        max_input_tokens=1000000, max_output_tokens=1000,
        shared_context_tokens=1001000, valid_until=None)
    return SyntheticCodexProof.create(**(values | changes))


def registry(*proofs, **changes):
    from services.api.app.application.provider_codex_profile import CodexProofRegistry
    return ProofRegistry(codex=CodexProofRegistry(proofs or [proof()], **changes)).codex


def assert_error(code, action, status=409):
    with pytest.raises(ApiError) as caught:
        action()
    assert (caught.value.status, caught.value.code) == (status, code)


def test_default_registry_exposes_empty_codex_admission():
    # Existing Provider-owned registry is the sole entry, never ordinary proofs.
    assert ProofRegistry().codex.freeze(BOOTSTRAP, tools()) is None


@pytest.mark.parametrize('text', ['ASCII', '中文', '😀 e\u0301', 'repeat ' * 80])
@pytest.mark.parametrize('kind', ['local_exact', 'local_upper_bound'])
def test_complete_synthetic_request_count_and_full_closure(text, kind):
    selected = proof(kind=kind)
    actual = registry(selected)
    profile = actual.freeze(BOOTSTRAP, tools())
    prepared = actual.prepare(config(), profile, messages(text), [], budget())
    body = strict_json(prepared.body)
    assert body['adapter'] == 'codex_app_server'
    assert body['version'] == 'codex-synthetic-model-request-v1'
    assert body['runtime'] == profile.model_dump(mode='json')
    assert body['turn']['messages'] == [value.model_dump() for value in messages(text)]
    assert body['turn']['max_output_tokens'] == 100
    assert body['resume']['bootstrap_sha256'] == BOOTSTRAP
    assert prepared.endpoint == 'http://127.0.0.1:4321/synthetic/codex-peer/model'
    for field in type(profile.closure).model_fields:
        if field != 'version':
            assert base64.b64decode(getattr(profile.closure, field), validate=True)
    count = (prepared.input_token_assurance.input_tokens if kind == 'local_exact'
        else prepared.input_token_assurance.input_tokens_upper_bound)
    assert count == (len(prepared.body) if kind == 'local_exact' else ((len(prepared.body) + 7) // 8) * 8)
    assert prepared.input_token_assurance.request_body_sha256 == sha256_bytes(prepared.body)
    assert prepared.cost_estimate.kind == 'unknown'
    assert actual.current(profile) == 'current'
    actual.verify(config(), profile, messages(text), [], budget(), prepared)


def test_absent_expired_withdrawn_and_replaced_proofs():
    selected = proof()
    actual = registry(selected)
    profile = actual.freeze(BOOTSTRAP, tools())
    prepared = actual.prepare(config(), profile, messages(), [], budget())
    for unavailable in [ProofRegistry().codex,
            registry(selected, withdrawn_proofs=[selected.sha256]),
            registry(proof(valid_until='2000-01-01T00:00:00Z'))]:
        assert unavailable.freeze(BOOTSTRAP, tools()) is None
        assert unavailable.current(profile) == 'unavailable'
        assert_error('CODEX_INPUT_PROOF_UNAVAILABLE',
            lambda: unavailable.verify(config(), profile, messages(), [], budget(), prepared), 503)
    assert actual.freeze('c' * 64, tools()) is None
    replacement = registry(proof(max_input_tokens=999999))
    assert replacement.current(profile) == 'changed'
    assert_error('CODEX_PROFILE_CHANGED',
        lambda: replacement.prepare(config(), profile, messages(), [], budget()))


def test_byte_changes_and_metadata_changes_rejected():
    actual = registry()
    profile = actual.freeze(BOOTSTRAP, tools())
    prepared = actual.prepare(config(), profile, messages(), [], budget())
    for altered in [replace(prepared, body=prepared.body + b' '),
            replace(prepared, body=prepared.body.replace(b'Only', b'Also')),
            replace(prepared, endpoint='http://127.0.0.1:4321/elsewhere'),
            replace(prepared, adapter_version='text-request-v2')]:
        assert_error('CODEX_SOURCE_CHANGED',
            lambda: actual.verify(config(), profile, messages(), [], budget(), altered))
    assert_error('CODEX_SOURCE_CHANGED',
        lambda: actual.verify(config(), profile, messages('changed'), [], budget(), prepared))


@pytest.mark.parametrize('changes', [dict(model='another'), dict(revision=3),
    dict(config_sha256='c' * 64), dict(base_url='http://127.0.0.1:4322/synthetic'),
    dict(base_url='http://127.0.0.1:4321/changed'), dict(adapter='compatible_chat'),
    dict(secret_present=False)])
def test_provider_destination_model_revision_secret_binding(changes):
    actual = registry()
    profile = actual.freeze(BOOTSTRAP, tools())
    assert actual.freeze(BOOTSTRAP, tools(), config=config(**changes)) is None
    assert_error('CODEX_INPUT_PROOF_UNAVAILABLE',
        lambda: actual.prepare(config(**changes), profile, messages(), [], budget()), 503)


def test_shared_capacity_input_output_and_cost_budgets():
    actual = registry()
    profile = actual.freeze(BOOTSTRAP, tools())
    for selected_budget in [budget(max_input_tokens=1), budget(max_output_tokens=1001)]:
        assert_error('CODEX_BUDGET_EXCEEDED',
            lambda: actual.prepare(config(), profile, messages(), [], selected_budget))
    shared = registry(proof(shared_context_tokens=100))
    assert_error('CODEX_BUDGET_EXCEEDED',
        lambda: shared.prepare(config(), shared.freeze(BOOTSTRAP, tools()), messages(), [], budget()))
    priced = config(pricing={'input_usd_per_million': 1.0, 'output_usd_per_million': 2.0, 'source_note': 'test'})
    priced_registry = registry(proof(config=priced))
    assert_error('CODEX_BUDGET_EXCEEDED', lambda: priced_registry.prepare(priced,
        priced_registry.freeze(BOOTSTRAP, tools()), messages(), [], budget(max_cost_usd=0.0)))


def test_strict_profile_closed_full_material_and_runtime_changes():
    from pydantic import ValidationError
    from services.api.app.application.provider_codex_profile import CodexRuntimeProfile
    actual = registry()
    profile = actual.freeze(BOOTSTRAP, tools())
    for changes in [dict(cpu_seconds=True), dict(extra='hidden'), dict(tools={'max_tool_calls': True, 'wall_seconds': 30})]:
        with pytest.raises(ValidationError):
            CodexRuntimeProfile.model_validate(profile.model_dump() | changes)
    mutated = profile.model_dump()
    mutated['closure']['environment'] = base64.b64encode(b'changed environment').decode()
    changed = CodexRuntimeProfile.model_validate(mutated)
    assert actual.current(changed) == 'changed'
    assert_error('CODEX_PROFILE_CHANGED', lambda: actual.prepare(config(), changed, messages(), [], budget()))
    for field in ['version', 'closure', 'proof_sha256']:
        missing = profile.model_dump()
        del missing[field]
        with pytest.raises(ValidationError):
            CodexRuntimeProfile.model_validate(missing)
    schema = CodexRuntimeProfile.model_json_schema()
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(schema['properties'])


def test_evidence_history_tool_definitions_and_all_fields_are_counted():
    actual = registry()
    profile = actual.freeze(BOOTSTRAP, tools())
    evidence = [dm.EvidenceChunk(ref=dm.ContentRef(entity='block', id='block_1', revision=1,
        sha256='d' * 64), locator='block:block_1@r1', text='材料 😀')]
    history = [messages()[0], dm.GenerationMessage(role='user', content='old task'),
        dm.GenerationMessage(role='assistant', content='old full answer'), messages()[1]]
    prepared = actual.prepare(config(), profile, history, evidence, budget())
    body = strict_json(prepared.body)
    assert body['turn']['evidence'] == [evidence[0].model_dump()]
    assert body['turn']['messages'] == [value.model_dump() for value in history]
    assert body['turn']['tools']['max_tool_calls'] == 2
    assert len(body['turn']['tool_definitions']) == 2
    assert prepared.input_token_assurance.input_tokens == len(prepared.body)
    hidden = strict_json(prepared.body)
    hidden['hidden_prompt'] = 'not allowed'
    assert_error('CODEX_SOURCE_CHANGED', lambda: actual.verify(config(), profile, history,
        evidence, budget(), replace(prepared, body=canonical_bytes(hidden))))


def test_ordinary_registry_remains_unavailable_even_with_codex_proof():
    actual = ProofRegistry(codex=registry())
    assert_error('CAPABILITY_UNSUPPORTED', lambda: actual.resolve(config()))


def test_registration_rejects_malformed_closure_real_models_and_borrowed_proofs():
    from pydantic import ValidationError
    from services.api.app.application.provider_codex_profile import CodexProofRegistry, SyntheticCodexProof
    selected = proof()
    corrupted = selected.model_dump()
    corrupted['closure']['network'] = base64.b64encode(b'allow network').decode()
    with pytest.raises(ValidationError):
        SyntheticCodexProof.model_validate(corrupted)
    with pytest.raises(ValidationError):
        proof(config=config(model='production-model'), model_versions=['production-model'])
    with pytest.raises(ValidationError):
        proof(config=config(base_url='https://example.com/v1', endpoint_policy='public_https'))
    with pytest.raises(ValueError):
        CodexProofRegistry([selected, selected])
    with pytest.raises(ValueError):
        CodexProofRegistry([object()])
    # Registration stores canonical private bytes; later caller mutation cannot
    # rewrite its reviewed config or actual model-version scope.
    installed = registry(selected)
    frozen = installed.freeze(BOOTSTRAP, tools())
    selected.config.model = 'changed'
    selected.model_versions.append('synthetic-extra')
    assert installed.current(frozen) == 'current'


def test_tools_history_and_shape_limits_never_extend_frozen_bytes():
    actual = registry()
    profile = actual.freeze(BOOTSTRAP, tools())
    prepared = actual.prepare(config(), profile, messages(), [], budget())
    new_profile = actual.freeze(BOOTSTRAP, CodexLocalToolBudget(max_tool_calls=0, wall_seconds=20))
    assert_error('CODEX_SOURCE_CHANGED',
        lambda: actual.verify(config(), new_profile, messages(), [], budget(), prepared))
    for unsupported in [[messages()[0]], messages() + [messages()[1]], messages() * 4]:
        assert_error('CODEX_INPUT_PROOF_UNAVAILABLE',
            lambda: actual.prepare(config(), profile, unsupported, [], budget()), 503)
    assert_error('CODEX_BUDGET_EXCEEDED',
        lambda: actual.prepare(config(), profile, messages('中' * 12001), [], budget()))
