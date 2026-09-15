"""Complete-input admission is bound to the exact reviewed service identity."""

import pytest
from dataclasses import replace

from services.api.app.application.errors import ApiError
from services.api.app.application.provider_budget import ProofRegistry, RequestPreparer
from tests.provider_protocol_fixture import test_preparer
from tests.unit.test_provider_budget import prepared_inputs


@pytest.fixture
def exact_profile(tmp_path):
    material, config, budget = prepared_inputs(tmp_path)
    return material, config, budget, test_preparer(config.base_url)


@pytest.mark.parametrize('url', ['http://localhost:8765/v1', 'http://127.0.0.1:8766/v1',
                                'http://127.0.0.1:8765/another'])
def test_same_model_name_on_another_endpoint_cannot_inherit_proof(exact_profile, url):
    material, config, budget, preparer = exact_profile
    assert preparer.prepare(config, material, budget).body
    other = config.model_copy(update={'base_url': url})
    with pytest.raises(ApiError) as refused:
        preparer.prepare(other, material, budget)
    assert refused.value.code == 'CAPABILITY_UNSUPPORTED'
    caps = preparer.capabilities(other, secret_available=True)
    assert not caps.chat and not caps.streaming


def test_responses_freezes_explicit_non_thinking_shape_before_counting(exact_profile):
    from packages.contracts.canonical import sha256_bytes, strict_json

    material, config, budget, preparer = exact_profile
    prepared = preparer.prepare(config, material, budget)
    body = strict_json(prepared.body)
    assert body.get('reasoning') == {'effort': 'none'}
    assert prepared.input_token_assurance.request_body_sha256 == sha256_bytes(prepared.body)
    assert prepared.input_token_assurance.input_tokens == len(prepared.body)


def test_expired_reviewed_basis_never_authorizes_a_new_request(exact_profile):
    from dataclasses import replace
    from services.api.app.application.provider_budget import ProofRegistry, RequestPreparer

    material, config, budget, preparer = exact_profile
    proof = preparer.registry.resolve(config)
    expired = replace(proof, valid_until='2000-01-01T00:00:00Z',
        validity_evidence=b'Artificial proof validity ended at the explicitly recorded deadline.')
    current = RequestPreparer(ProofRegistry([expired]))
    with pytest.raises(ApiError) as refused:
        current.prepare(config, material, budget)
    assert refused.value.code == 'CAPABILITY_UNSUPPORTED'
    assert not current.capabilities(config, secret_available=True).chat


def test_endpoint_normalization_uses_the_actual_transport_rules_without_dns(exact_profile, monkeypatch):
    import socket

    material, config, budget, preparer = exact_profile
    config = config.model_copy(update={'base_url': 'https://PROOF.EXAMPLE:443/v1/', 'endpoint_policy': 'public_https'})
    # Synthetic local admission calculation only: this domain is not contacted
    # or asserted to implement this artificial model.
    proof = replace(preparer.registry.resolve(exact_profile[1]), base_url=config.base_url,
                    endpoint_policy=config.endpoint_policy)
    current = RequestPreparer(ProofRegistry([proof]))
    def forbidden_dns(*args, **kwargs):
        raise AssertionError('Local proof lookup must not resolve the network.')
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden_dns)
    normalized = config.model_copy(update={'base_url': 'https://proof.example/v1'})
    assert current.prepare(config, material, budget) == current.prepare(normalized, material, budget)
    assert replace(proof, base_url=normalized.base_url).sha256 == proof.sha256
    with pytest.raises(ValueError, match='duplicate'):
        ProofRegistry([proof, replace(proof, base_url=normalized.base_url)])


def test_model_and_endpoint_policy_cannot_reuse_an_exact_registration(exact_profile):
    material, config, budget, preparer = exact_profile
    for changes in ({'model': 'another-synthetic-model'}, {'endpoint_policy': 'public_https'}):
        with pytest.raises(ApiError) as refused:
            preparer.prepare(config.model_copy(update=changes), material, budget)
        assert refused.value.code == 'CAPABILITY_UNSUPPORTED'


def test_reviewed_scope_and_validity_bytes_are_bound_not_only_the_checker_name(exact_profile):
    proof = exact_profile[3].registry.resolve(exact_profile[1])
    alternatives = [replace(proof, model_versions=('synthetic-revision-2',)),
        replace(proof, validity_evidence=proof.validity_evidence + b' revision 2'),
        replace(proof, valid_until='2030-01-01T00:00:00Z'),
        replace(proof, base_url='http://127.0.0.1:8766/v1'),
        replace(proof, checker_version='synthetic-counter-v3'),
        replace(proof, max_output_tokens=proof.max_output_tokens + 1),
        replace(proof, evidence=proof.evidence + b' additional checked rule')]
    assert len({proof.sha256, *(value.sha256 for value in alternatives)}) == len(alternatives) + 1
    for changes in ({'adapter_version': 'text-request-v1'}, {'input_shape': 'old-shape'},
                    {'model_versions': ()}, {'model_versions': ('*',)}, {'validity_evidence': b''}):
        with pytest.raises(ValueError):
            ProofRegistry([replace(proof, **changes)])


def test_responses_checker_rejects_implicit_or_changed_thinking(exact_profile):
    from packages.contracts.canonical import canonical_bytes, strict_json

    material, config, budget, preparer = exact_profile
    body = strict_json(preparer.prepare(config, material, budget).body)
    proof = preparer.registry.resolve(config)
    missing = dict(body)
    missing.pop('reasoning')
    for changed in (missing, dict(body, reasoning={'effort': 'low'})):
        with pytest.raises(ValueError):
            proof.check(canonical_bytes(changed))
