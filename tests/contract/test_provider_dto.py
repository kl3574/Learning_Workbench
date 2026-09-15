"""Synthetic shape/counterexample checks, not source proofs or external calls."""

from copy import deepcopy
from pathlib import Path
from typing import get_args

import jsonschema
from pydantic import TypeAdapter, ValidationError
import pytest

from packages.contracts import domain_models as dm
from services.api.app import provider_dto as dto
from services.api.app.application import provider_models as private


NOW = '2026-09-15T01:00:00Z'
LATER = '2026-09-15T02:00:00Z'
HASH = 'a' * 64


def config():
    return {'expected_revision': 0, 'adapter': 'official_responses',
            'base_url': 'https://example.invalid/v1', 'model': 'synthetic-model',
            'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None}


def budget():
    return {'max_input_tokens': 100, 'max_output_tokens': 20, 'max_provider_calls': 1,
            'max_search_calls': 0, 'max_tool_calls': 0, 'max_cost_usd': None}


def summary():
    return {'job_id': 'job_one', 'source_job_revision': 1, 'source_input_sha256': HASH,
            'purpose': 'tutor', 'provider_id': 'provider_one', 'provider_revision': 1,
            'config_sha256': HASH, 'adapter': 'official_responses', 'adapter_version': 'synthetic-v1',
            'base_url': 'https://example.invalid/v1', 'endpoint_policy': 'public_https',
            'model': 'synthetic-model', 'context_snapshot_id': 'context_one',
            'context_snapshot_sha256': HASH, 'input_sha256': HASH,
            'messages': [{'role': 'user', 'character_count': 2, 'content_sha256': HASH}],
            'references': [], 'input_character_count': 2,
            'input_token_assurance': {'kind': 'local_exact', 'input_tokens': 3,
                                      'checker_version': 'synthetic-v1', 'proof_sha256': HASH,
                                      'request_body_sha256': HASH},
            'allow_web': False, 'budget': {**budget(), 'timeout_seconds': 180},
            'cost_estimate': {'kind': 'unknown', 'currency': 'USD'},
            'created_at': NOW, 'expires_at': LATER}


def consent():
    return {'id': 'consent_one', 'revision': 1, 'status': 'active',
            'proposal_id': 'proposal_one', 'proposal_sha256': HASH, 'summary': summary(),
            'created_at': NOW, 'expires_at': LATER, 'revoked_at': None, 'dispatch': None}


def usage():
    return {'consumed_provider_calls': 1, 'search_calls': 0, 'tool_calls': 0,
            'input_tokens': None, 'output_tokens': None, 'elapsed_ms': None,
            'cost': {'kind': 'unknown', 'currency': 'USD'}}


def finished():
    return {'type': 'finished', 'outcome': 'complete', 'reason': None,
            'output_state': 'complete', 'usage': {'input_tokens': None, 'output_tokens': None}}


def receipt():
    return {'id': 'receipt_one', 'workspace_id': 'workspace_one', 'dispatch_id': 'dispatch_one',
            'job_id': 'job_one', 'consent_id': 'consent_one', 'proposal_id': 'proposal_one',
            'request_body_sha256': HASH, 'terminal': finished(),
            'answer_artifact_id': 'artifact_answer', 'refusal_artifact_id': None,
            'recorded_at': NOW, 'receipt_sha256': HASH}


def prepared():
    return {'job_id': 'job_one', 'job_revision': 1, 'job_input_sha256': HASH, 'purpose': 'tutor',
            'context_snapshot': {'id': 'context_one', 'created_at': NOW, 'request_sha256': HASH,
                                 'resolved_refs': [], 'policy': 'learning', 'character_count': 2,
                                 'snapshot_sha256': HASH},
            'messages': [{'role': 'user', 'content': '你好'}], 'evidence': [],
            'preparation_version': 'synthetic-v1', 'prepared_input_sha256': HASH}


def public_samples():
    config_view = {key: value for key, value in config().items() if key != 'expected_revision'}
    config_view.update(id='provider_one', revision=1, config_sha256=HASH,
                       configured=True, secret_present=False)
    ack = {key: config_view[key] for key in ['id', 'revision', 'config_sha256', 'configured', 'secret_present']}
    secret_ack = {key: value for key, value in ack.items() if key != 'configured'}
    exact = summary()['input_token_assurance']
    upper = {key: value for key, value in exact.items() if key != 'input_tokens'}
    upper.update(kind='local_upper_bound', input_tokens_upper_bound=5)
    return [
        (dto.ProviderPricing, {'input_usd_per_million': 0, 'output_usd_per_million': 0.5,
                               'source_note': '合成契约样例'}),
        (dto.ProviderCapabilitiesResponse, {'items': []}),
        (dto.ProviderConfigWrite, config()), (dto.ProviderConfigView, config_view),
        (dto.ProviderConfigAck, ack),
        (dto.ProviderSecretWrite, {'expected_revision': 1, 'secret': 'synthetic-private-input'}),
        (dto.ProviderSecretAck, secret_ack), (dto.OutboundBudget, budget()),
        (dto.FrozenOutboundBudget, {**budget(), 'timeout_seconds': 180}),
        (dto.ConsentPreviewWrite, {'job_id': 'job_one', 'expected_job_revision': 1,
                                  'provider_id': 'provider_one', 'expected_provider_revision': 1,
                                  'budget': budget(), 'expires_at': LATER}),
        (dto.ReferenceSummary, {'ref': {'entity': 'block', 'id': 'block_one', 'revision': 1, 'sha256': HASH},
                                'title': '合成标题', 'locator': '第1节', 'character_count': 2,
                                'excerpt_sha256': HASH}),
        (dto.MessageSummary, summary()['messages'][0]),
        (dto.LocalExactInputTokens, exact), (dto.LocalUpperBoundInputTokens, upper),
        (dto.UnknownCostEstimate, {'kind': 'unknown', 'currency': 'USD'}),
        (dto.EstimatedCostEstimate, {'kind': 'estimated', 'currency': 'USD',
                                     'maximum_estimated_cost': 0.5, 'pricing_sha256': HASH}),
        (dto.FrozenOutboundSummary, summary()),
        (dto.ProposalWarning, {'code': 'price_unknown', 'message': '未提供价格。'}),
        (dto.ConsentProposalView, {'id': 'proposal_one', 'proposal_sha256': HASH, 'summary': summary(),
                                   'validity': 'current', 'consent_id': None, 'warnings': []}),
        (dto.ConsentCreate, {'proposal_id': 'proposal_one', 'proposal_sha256': HASH}),
        (dto.ConsentCreateAck, {'id': 'consent_one', 'revision': 1, 'status': 'active',
                                'proposal_id': 'proposal_one', 'proposal_sha256': HASH, 'summary': summary()}),
        (dto.ConsentRevoke, {'expected_revision': 1}),
        (dto.UnknownUsageCost, {'kind': 'unknown', 'currency': 'USD'}),
        (dto.EstimatedUsageCost, {'kind': 'estimated', 'currency': 'USD', 'amount': 0,
                                 'pricing_sha256': HASH}),
        (dto.ActualUsageCost, {'kind': 'actual', 'currency': 'USD', 'amount': 0,
                              'source': 'provider_reported'}),
        (dto.ProviderUsageView, usage()), (dto.ConsentView, consent()),
        (dto.ConsentDispatchView, {'id': 'dispatch_one', 'job': {'id': 'job_one', 'status': 'running'},
                                   'started_at': NOW, 'finished_at': None, 'usage': usage(), 'error_code': None}),
        (dto.ConsentByIdQuery, {'consent_id': 'consent_one'}), (dto.ConsentListQuery, {}),
        (dto.ConsentPage, {'items': [consent()], 'next_cursor': None}),
    ]


@pytest.mark.parametrize('model,value', public_samples(), ids=lambda value: value.__name__ if isinstance(value, type) else None)
def test_public_shapes_are_closed_required_and_schema_serializable(model, value):
    result = model.model_validate(value)
    schema = model.model_json_schema(mode='serialization')
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(result.model_dump(mode='json'), schema)
    with pytest.raises(ValidationError):
        model.model_validate({**value, 'undeclared_field': True})
    for name, field in model.model_fields.items():
        if field.is_required():
            missing = deepcopy(value)
            del missing[name]
            with pytest.raises(ValidationError):
                model.model_validate(missing)


def test_frozen_core_is_unchanged_and_job_ref_is_reused():
    assert len(dm.CONTRACTS) == 54
    assert dto.JobRef is dm.JobRef
    root = Path(__file__).resolve().parents[2]
    spec = (root / 'PRODUCT_DESIGN.md').read_text()
    embedded = spec.split('<!-- BEGIN FILE: packages/contracts/domain_models.py -->\n~~~python\n')[1].split('\n~~~')[0]
    assert embedded + '\n' == (root / 'packages/contracts/domain_models.py').read_text()


@pytest.mark.parametrize('field,bad', [
    ('max_provider_calls', True), ('max_provider_calls', 1.0), ('max_provider_calls', '1'),
    ('max_search_calls', False), ('max_search_calls', 0.0), ('max_tool_calls', False),
    ('max_input_tokens', True), ('max_input_tokens', 0), ('max_output_tokens', 1.5),
    ('timeout_seconds', False), ('timeout_seconds', None), ('max_cost_usd', True),
    ('max_cost_usd', float('nan')), ('max_cost_usd', float('inf')), ('max_cost_usd', -0.01),
])
def test_budget_rejects_literal_coercion_nonfinite_and_illegal_ranges(field, bad):
    with pytest.raises(ValidationError):
        dto.OutboundBudget.model_validate({**budget(), field: bad})


@pytest.mark.parametrize('field', ['base_url', 'model', 'embedding_model'])
@pytest.mark.parametrize('blank', ['', ' \n\t', '\u3000'])
def test_configuration_strings_do_not_normalize_blank_into_configuration(field, blank):
    with pytest.raises(ValidationError):
        dto.ProviderConfigWrite.model_validate({**config(), field: blank})


def test_sensitive_write_repr_and_strict_boolean_values():
    secret = dto.ProviderSecretWrite(expected_revision=1, secret='synthetic-private-input')
    assert 'synthetic-private-input' not in repr(secret)
    for secret_value in ['', ' \t', True, 123]:
        with pytest.raises(ValidationError):
            dto.ProviderSecretWrite.model_validate({'expected_revision': 1, 'secret': secret_value})
    ack = {'id': 'provider_one', 'revision': 1, 'config_sha256': HASH, 'configured': True, 'secret_present': False}
    for field, bad in [('configured', 1), ('configured', 'true'), ('secret_present', 0), ('secret_present', 'false')]:
        with pytest.raises(ValidationError):
            dto.ProviderConfigAck.model_validate({**ack, field: bad})
    for bad in [0, 0.0, 'false', True]:
        with pytest.raises(ValidationError):
            dto.FrozenOutboundSummary.model_validate({**summary(), 'allow_web': bad})
    ack = {'id': 'consent_one', 'revision': 1, 'status': 'active', 'proposal_id': 'proposal_one',
           'proposal_sha256': HASH, 'summary': summary()}
    for bad in [True, 1.0, '1']:
        with pytest.raises(ValidationError):
            dto.ConsentCreateAck.model_validate({**ack, 'revision': bad})


def test_omitted_timeout_is_normalized_but_all_frozen_fields_remain_required():
    omitted = dto.OutboundBudget.model_validate(budget())
    explicit = dto.OutboundBudget.model_validate({**budget(), 'timeout_seconds': 180})
    assert omitted.model_dump(mode='json') == explicit.model_dump(mode='json')
    with pytest.raises(ValidationError):
        dto.FrozenOutboundBudget.model_validate(budget())
    frozen = dto.FrozenOutboundBudget.model_validate(omitted.model_dump())
    assert frozen.timeout_seconds == 180 and frozen.max_cost_usd is None


def test_query_modes_and_optional_nonnullable_fields():
    query = TypeAdapter(dto.ConsentQuery)
    assert isinstance(query.validate_python({}), dto.ConsentListQuery)
    assert isinstance(query.validate_python({'consent_id': 'consent_one'}), dto.ConsentByIdQuery)
    for bad in [{'consent_id': 'consent_one', 'limit': 20}, {'consent_id': 'consent_one', 'cursor': 'signed'},
                {'cursor': None}, {'cursor': ' '}, {'limit': None}, {'limit': True}, {'limit': 101}, {'other': 1}]:
        with pytest.raises(ValidationError):
            query.validate_python(bad)
    page = {'items': [], 'next_cursor': None}
    assert dto.ConsentPage.model_validate(page).model_dump() == page
    assert dto.ConsentPage.model_validate({**page, 'total_hint': 0}).model_dump()['total_hint'] == 0
    for bad in [None, True, -1, '0']:
        with pytest.raises(ValidationError):
            dto.ConsentPage.model_validate({**page, 'total_hint': bad})
    for model, field in [(dto.ConsentListQuery, 'cursor'), (dto.ConsentPage, 'total_hint')]:
        schema = model.model_json_schema()
        assert field not in schema.get('required', [])
        assert 'null' not in str(schema['properties'][field].get('anyOf', []))
        assert 'default' not in schema['properties'][field]


def test_token_and_cost_variants_do_not_accept_mixed_or_invented_proofs():
    assurance = TypeAdapter(dto.InputTokenAssurance)
    exact = summary()['input_token_assurance']
    for bad in [{**exact, 'input_tokens_upper_bound': 3}, {**exact, 'kind': 'remote_count'},
                {**exact, 'input_tokens': True}, {**exact, 'proof_sha256': 'bad'},
                {**exact, 'checker_version': '  '}]:
        with pytest.raises(ValidationError):
            assurance.validate_python(bad)
    estimate = TypeAdapter(dto.CostEstimate)
    for bad in [{'kind': 'unknown', 'currency': 'USD', 'maximum_estimated_cost': 0},
                {'kind': 'actual', 'currency': 'USD', 'amount': 0},
                {'kind': 'estimated', 'currency': 'USD', 'maximum_estimated_cost': 0.5}]:
        with pytest.raises(ValidationError):
            estimate.validate_python(bad)
    costs = TypeAdapter(dto.UsageCost)
    for bad in [{'kind': 'actual', 'currency': 'USD', 'amount': 0, 'source': 'local_rate'},
                {'kind': 'unknown', 'currency': 'USD', 'amount': 0},
                {'kind': 'estimated', 'currency': 'USD', 'amount': float('inf'), 'pricing_sha256': HASH}]:
        with pytest.raises(ValidationError):
            costs.validate_python(bad)


def test_frozen_limits_validate_dates_and_bounds_without_rechecking_current_clock():
    # An expired historical ACK remains structurally readable; live expiry is a service check.
    frozen = summary()
    frozen['created_at'] = '2020-01-01T00:00:00.1Z'
    frozen['expires_at'] = '2020-01-01T00:00:00.2Z'
    dto.FrozenOutboundSummary.model_validate(frozen)
    for expires in ['2020-01-01T00:00:00.1Z', '2020-01-01T00:00:00Z', '2020-02-31T00:00:00Z']:
        with pytest.raises(ValidationError):
            dto.FrozenOutboundSummary.model_validate({**frozen, 'expires_at': expires})
    for variant, field in [('local_exact', 'input_tokens'), ('local_upper_bound', 'input_tokens_upper_bound')]:
        frozen = summary()
        frozen['input_token_assurance'] = {'kind': variant, field: 101, 'checker_version': 'synthetic-v1',
                                         'proof_sha256': HASH, 'request_body_sha256': HASH}
        with pytest.raises(ValidationError):
            dto.FrozenOutboundSummary.model_validate(frozen)
    frozen = summary()
    frozen['budget']['max_cost_usd'] = 0.5
    frozen['cost_estimate'] = {'kind': 'estimated', 'currency': 'USD',
                               'maximum_estimated_cost': 0.6, 'pricing_sha256': HASH}
    with pytest.raises(ValidationError):
        dto.FrozenOutboundSummary.model_validate(frozen)
    frozen['cost_estimate'] = {'kind': 'unknown', 'currency': 'USD'}
    dto.FrozenOutboundSummary.model_validate(frozen)


@pytest.mark.parametrize('change', [
    {'expires_at': '2026-09-15T03:00:00Z'}, {'status': 'revoked'}, {'revoked_at': NOW},
    {'created_at': LATER}, {'status': 'revoked', 'revoked_at': '2026-09-15T00:00:00Z'},
])
def test_consent_cannot_rewrite_expiry_or_invent_revocation(change):
    with pytest.raises(ValidationError):
        dto.ConsentView.model_validate({**consent(), **change})


def test_current_consent_and_original_active_ack_are_distinct_models():
    dto.ConsentView.model_validate({**consent(), 'revision': 2, 'status': 'revoked', 'revoked_at': LATER})
    ack = dto.ConsentCreateAck.model_validate({'id': 'consent_one', 'revision': 1, 'status': 'active',
                                              'proposal_id': 'proposal_one', 'proposal_sha256': HASH,
                                              'summary': summary()})
    assert ack.status == 'active' and ack.revision == 1


def test_unknown_usage_remains_unknown_and_real_overrun_is_not_hidden():
    model = dto.ProviderUsageView.model_validate(usage())
    assert model.input_tokens is None and model.cost.kind == 'unknown'
    assert dto.ProviderUsageView.model_validate({**usage(), 'input_tokens': 1000000}).input_tokens == 1000000
    for field, bad in [('consumed_provider_calls', 2), ('consumed_provider_calls', True),
                       ('input_tokens', True), ('output_tokens', -1), ('elapsed_ms', 1.5),
                       ('search_calls', False), ('tool_calls', 1)]:
        with pytest.raises(ValidationError):
            dto.ProviderUsageView.model_validate({**usage(), field: bad})


def test_dispatch_job_terminal_and_provider_terminal_are_not_the_same_fact():
    value = {'id': 'dispatch_one', 'job': {'id': 'job_one', 'status': 'running'},
             'started_at': NOW, 'finished_at': LATER, 'usage': usage(), 'error_code': 'PROVIDER_INCOMPLETE'}
    assert dto.ConsentDispatchView.model_validate(value).job.status == 'running'
    with pytest.raises(ValidationError):
        dto.ConsentDispatchView.model_validate({**value, 'finished_at': '2026-09-15T00:00:00Z'})


def test_private_prepared_material_reuses_closed_core_context_and_messages():
    value = private.PreparedOutboundMaterial.model_validate(prepared())
    assert type(value.context_snapshot) is dm.ContextSnapshot
    assert type(value.messages[0]) is dm.GenerationMessage
    for field, bad in [('job_revision', True), ('consent_id', 'consent_fake'), ('preparation_version', ' '),
                       ('messages', [{'role': 'user', 'content': 'x', 'tool_calls': []}])]:
        with pytest.raises(ValidationError):
            private.PreparedOutboundMaterial.model_validate({**prepared(), field: bad})
    private.DispatchLease(owner_id='owner_one', job_revision=1, expires_at=NOW)
    with pytest.raises(ValidationError):
        private.DispatchLease(owner_id='owner_one', job_revision=True, expires_at=NOW)


@pytest.mark.parametrize('event', [
    {'type': 'delta', 'channel': 'answer', 'text': '合成'},
    {'type': 'delta', 'channel': 'refusal', 'text': '拒答'},
    {'type': 'delta', 'channel': 'answer', 'text': ' '},
    {'type': 'delta', 'channel': 'answer', 'text': '\n'},
    {'type': 'usage', 'input_tokens': 0, 'output_tokens': None},
    finished(),
    {'type': 'finished', 'outcome': 'refused', 'reason': None, 'output_state': 'complete',
     'usage': {'input_tokens': 2, 'output_tokens': 1}},
    {'type': 'finished', 'outcome': 'incomplete', 'reason': 'output_limit', 'output_state': 'partial',
     'usage': {'input_tokens': None, 'output_tokens': 1}},
    {'type': 'error', 'error_code': 'PROVIDER_USAGE_INCONSISTENT', 'provider_outcome': 'completed',
     'output_state': 'partial', 'usage': {'input_tokens': 1000000, 'output_tokens': None}},
])
def test_four_checked_event_shapes_preserve_facts_and_reject_extras(event):
    adapter = TypeAdapter(private.CheckedProviderEvent)
    result = adapter.validate_python(event)
    if result.type == 'delta':
        assert result.text == event['text']
    jsonschema.validate(result.model_dump(mode='json'), adapter.json_schema())
    with pytest.raises(ValidationError):
        adapter.validate_python({**event, 'sdk_payload': {}})
    for name in type(result).model_fields:
        missing = deepcopy(event)
        del missing[name]
        with pytest.raises(ValidationError):
            adapter.validate_python(missing)


@pytest.mark.parametrize('event', [
    {'type': 'delta', 'channel': 'answer', 'text': ''},
    {'type': 'delta', 'channel': 'tool', 'text': 'x'},
    {'type': 'usage', 'input_tokens': None, 'output_tokens': None},
    {'type': 'usage', 'input_tokens': True, 'output_tokens': None},
    {**finished(), 'outcome': 'incomplete'},
    {**finished(), 'outcome': 'incomplete', 'reason': 'output_limit'},
    {**finished(), 'outcome': 'refused', 'reason': 'content_filter'},
    {**finished(), 'output_state': 'partial'},
    {**finished(), 'reason': 'output_limit'},
    {'type': 'error', 'error_code': 'PROVIDER_TIMEOUT', 'provider_outcome': 'unknown',
     'output_state': 'complete', 'usage': {'input_tokens': None, 'output_tokens': None}},
])
def test_events_reject_false_success_and_fabricated_usage(event):
    with pytest.raises(ValidationError):
        TypeAdapter(private.CheckedProviderEvent).validate_python(event)


@pytest.mark.parametrize('code', get_args(dto.ProviderFailureCode))
def test_all_seventeen_spec_failures_preserve_unknown_remote_outcome(code):
    event = private.CheckedProviderError(type='error', error_code=code, provider_outcome='unknown',
                                         output_state='none', usage=private.UsageSnapshot(input_tokens=None, output_tokens=None))
    assert event.provider_outcome == 'unknown' and event.usage.input_tokens is None
    assert len(get_args(dto.ProviderFailureCode)) == 17


def test_receipt_requires_terminal_and_preserves_both_partial_channels():
    private.ProviderTerminalReceipt.model_validate(receipt())
    error = {'type': 'error', 'error_code': 'PROVIDER_USAGE_INCONSISTENT', 'provider_outcome': 'completed',
             'output_state': 'partial', 'usage': {'input_tokens': 1000000, 'output_tokens': None}}
    value = {**receipt(), 'terminal': error, 'refusal_artifact_id': 'artifact_refusal'}
    assert private.ProviderTerminalReceipt.model_validate(value).refusal_artifact_id == 'artifact_refusal'
    for changed in [
        {'terminal': {'type': 'usage', 'input_tokens': 1, 'output_tokens': None}},
        {'answer_artifact_id': None}, {'refusal_artifact_id': 'artifact_refusal'},
        {'terminal': {**finished(), 'output_state': 'none'}},
        {'terminal': {**finished(), 'outcome': 'refused'}},
    ]:
        with pytest.raises(ValidationError):
            private.ProviderTerminalReceipt.model_validate({**receipt(), **changed})
    refused = {**receipt(), 'terminal': {**finished(), 'outcome': 'refused'},
               'refusal_artifact_id': 'artifact_refusal'}
    private.ProviderTerminalReceipt.model_validate(refused)


def test_public_schema_contains_no_private_preparation_or_secret_response_fields():
    schema = dto.ConsentPage.model_json_schema()
    names = set(schema['$defs'])
    assert not names & {'PreparedOutboundMaterial', 'GenerationMessage', 'EvidenceChunk', 'ProviderTerminalReceipt'}
    for model in [dto.ProviderConfigView, dto.ProviderConfigAck, dto.ProviderSecretAck,
                  dto.ConsentProposalView, dto.ConsentCreateAck, dto.ConsentPage]:
        assert 'secret' not in model.model_json_schema()['properties']
    assert dto.ConsentPage.model_json_schema()['$defs']['JobRef']['additionalProperties'] is False
