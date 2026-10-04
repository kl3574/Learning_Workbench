"""Synthetic contract checks; no runtime registration, database, or external calls."""
from copy import deepcopy
import json
import re

import jsonschema
import pytest
from pydantic import ValidationError

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from scripts.codex_turn_contracts import MODEL_NAMES, codex_turn_artifacts
from services.api.app import codex_bootstrap_dto as bootstrap
from services.api.app import codex_turn_dto as dto
from codex_turn_samples import HASH, LATER, NOW, samples


@pytest.mark.parametrize('name', MODEL_NAMES)
def test_every_closed_object_has_required_fields_and_roundtrips_without_defaults(name):
    model = getattr(dto, name)
    value = samples()[name]
    decoded = model.model_validate(value)
    assert decoded.model_dump(mode='json') == value
    assert model.model_validate_json(json.dumps(value)).model_dump(mode='json') == value
    schema = model.model_json_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(value, schema)
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(schema['properties'])
    for field in value:
        missing = deepcopy(value)
        del missing[field]
        with pytest.raises(ValidationError):
            model.model_validate(missing)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(missing, schema)
    with pytest.raises(ValidationError):
        model.model_validate({**value, 'unreviewed_extra': None})


@pytest.mark.parametrize('name,path,value', [
    ('CodexTurnPrepareWrite', ('message',), ' \n'),
    ('CodexTurnPrepareWrite', ('message',), '\ud800'),
    ('CodexTurnPrepareWrite', ('message',), 'a' * 8001),
    ('CodexTurnPrepareWrite', ('expected_session_revision',), True),
    ('CodexTurnPrepareWrite', ('context_refs', 0, 'entity'), 'question'),
    ('CodexLocalToolBudget', ('max_tool_calls',), True),
    ('CodexLocalToolBudget', ('max_tool_calls',), 17),
    ('CodexLocalToolBudget', ('wall_seconds',), 301),
    ('CodexLocalToolBudget', ('wall_seconds',), 0),
    ('CodexTurnRuntimeSummary', ('cpu_seconds',), 60.0),
    ('CodexTurnRuntimeSummary', ('core_bytes',), False),
    ('CodexTurnRuntimeSummary', ('command_network',), 'allowed'),
    ('CodexTurnRuntimeSummary', ('memory_bytes',), 2147483649),
    ('CodexOutboundBudgetWrite', ('max_provider_calls',), True),
    ('CodexOutboundBudgetWrite', ('max_search_calls',), False),
    ('CodexOutboundBudgetWrite', ('max_provider_calls',), 2),
    ('CodexOutboundBudgetWrite', ('max_cost_usd',), float('nan')),
    ('CodexOutboundBudgetWrite', ('max_cost_usd',), float('inf')),
    ('CodexOutboundBudgetWrite', ('max_cost_usd',), True),
    ('CodexFrozenOutboundSummary', ('messages', 0, 'character_count'), True),
    ('CodexFrozenOutboundSummary', ('references', 0, 'title'), '\udfff'),
    ('CodexFrozenOutboundSummary', ('adapter',), 'compatible_chat'),
    ('CodexFrozenOutboundSummary', ('endpoint',), 'https://synthetic:synthetic@example.invalid/v1'),
    ('CodexFrozenOutboundSummary', ('endpoint',), 'http://example.invalid/v1'),
    ('CodexFrozenOutboundSummary', ('endpoint_policy',), 'explicit_loopback'),
    ('CodexFrozenOutboundSummary', ('expires_at',), '2026-10-04T00:10:01Z'),
    ('CodexFrozenOutboundSummary', ('input_token_assurance', 'request_body_sha256'), 'b' * 64),
    ('CodexFrozenOutboundSummary', ('input_token_assurance', 'input_tokens'), 101),
    ('CodexTurnControlView', ('cancel_requested',), 1),
    ('CodexTurnControlView', ('error_code',), 'unbounded upstream raw error'),
    ('CodexTurnResultView', ('output_sha256',), 'b' * 64),
    ('CodexTurnResultView', ('output_state',), 'none'),
    ('CodexTurnResultView', ('mathematical',), 'PASS'),
    ('CodexTurnEvent', ('seq',), 0),
    ('CodexTurnEvent', ('payload', 'job', 'id'), 'foreign_job'),
    ('CodexConsentView', ('revision',), 2),
    ('CodexConsentView', ('dispatch', 'job', 'id'), 'foreign_job'),
    ('CodexConsentView', ('expires_at',), '2026-10-04T00:06:00Z'),
    ('CodexConsentView', ('status',), 'revoked'),
    ('CodexConsentCreateAck', ('revision',), 2),
    ('CodexApprovalControl', ('decision',), 'decline'),
    ('GenericApprovalDecisionAck', ('revision',), 3),
    ('GenericApprovalDecisionAck', ('applied',), 1),
    ('GenericApprovalView', ('run_id',), 'foreign_job'),
    ('CodexTurnStartAck', ('job', 'status'), 'completed'),
    ('CodexArtifactManifest', ('run_id',), 'foreign_job'),
    ('CodexArtifactManifest', ('total_bytes',), 3),
    ('CodexArtifactManifest', ('entries', 0, 'size'), True),
    ('CodexArtifactManifest', ('excluded', 0, 'entry_id'), 'artifact_one'),
    ('CodexArtifactManifestView', ('manifest', 'entries', 0, 'sha256'), 'b' * 64),
    ('CodexArtifactImportView', ('items', 0, 'job', 'id'), 'aggregate_job'),
])
def test_rejects_semantic_counterexamples(name, path, value):
    sample = samples()[name]
    target = sample
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        getattr(dto, name).model_validate(sample)


def test_order_and_exact_ref_binding_survive_preparation_and_whole_item_omission():
    sample = samples()['CodexTurnPreparationView']
    # Separate the request and summary aliases in the synthetic builder.
    sample = json.loads(json.dumps(sample))
    first = {**sample['request']['context_refs'][0], 'id': 'block_first'}
    sample['request']['context_refs'].append(first)
    sample['summary']['materials'].append({**sample['summary']['materials'][0], 'ref': first})
    decoded = dto.CodexTurnPreparationView.model_validate(sample)
    assert [m.ref.id for m in decoded.summary.materials] == ['block_second', 'block_first']
    for mutate in ('reverse', 'replace', 'duplicate', 'tools', 'self_history', 'consent', 'revision'):
        bad = deepcopy(sample)
        if mutate == 'reverse':
            bad['summary']['materials'].reverse()
        elif mutate == 'replace':
            bad['summary']['materials'][0]['ref']['sha256'] = 'b' * 64
        elif mutate == 'duplicate':
            bad['request']['context_refs'].append(deepcopy(bad['request']['context_refs'][0]))
        elif mutate == 'tools':
            bad['summary']['tools'] = {**bad['summary']['tools'], 'max_tool_calls': 16}
        elif mutate == 'self_history':
            bad['summary']['history_turn_ids'] = [bad['turn_id']]
        elif mutate == 'consent':
            bad['consent_id'] = 'consent_without_proposal'
        else:
            bad['session_revision'] = bad['request']['expected_session_revision']
        with pytest.raises(ValidationError):
            dto.CodexTurnPreparationView.model_validate(bad)
    sample['summary']['materials'] = sample['summary']['materials'][1:]
    assert dto.CodexTurnPreparationView.model_validate(sample).summary.materials[0].ref.id == 'block_first'


def test_safe_control_has_complete_ordered_basis_and_retains_consumed_or_closed_grant():
    value = samples()['CodexTurnControlView']
    value['approval_ids'].append('approval_two')
    value['approval_controls'].append({**value['approval_controls'][0], 'id': 'approval_two',
                                       'decision': 'decline', 'revision': 2, 'validity': 'closed'})
    for change in ('reverse', 'missing', 'duplicate', 'foreign'):
        bad = deepcopy(value)
        if change == 'reverse':
            bad['approval_controls'].reverse()
        elif change == 'missing':
            bad['approval_controls'].pop()
        elif change == 'duplicate':
            bad['approval_ids'][1] = bad['approval_ids'][0]
        else:
            bad['approval_controls'][0]['id'] = 'foreign_approval'
        with pytest.raises(ValidationError):
            dto.CodexTurnControlView.model_validate(bad)
    value.update(execution='terminal', outcome='unknown', finished_at=LATER,
                 error_code='CODEX_OUTCOME_UNKNOWN', job={'id': 'job_one', 'status': 'failed'})
    for status, revision in [('active', 1), ('expired', 1), ('revoked', 2)]:
        value['consent_control'].update(status=status, revision=revision)
        decoded = dto.CodexTurnControlView.model_validate(value)
        assert decoded.consent_control.id == 'consent_one'
        assert decoded.approval_ids == [item.id for item in decoded.approval_controls]
    # The DTO cannot infer that an absent consent was historically deleted;
    # owner membership validation, not a fabricated default, supplies that proof.
    assert 'consent_control' in dto.CodexTurnControlView.model_fields


@pytest.mark.parametrize('payload_name', [name for name in MODEL_NAMES if name.endswith('Event') and name != 'CodexTurnEvent'])
def test_sse_union_is_discriminated_closed_and_preserves_raw_whitespace(payload_name):
    event = samples()['CodexTurnEvent']
    event['payload'] = samples()[payload_name]
    assert dto.CodexTurnEvent.model_validate(event).model_dump() == event
    for extra in ({'type': 'raw_protocol'}, {'upstream_id': 'never_public'}, {'seq': 2}):
        with pytest.raises(ValidationError):
            dto.CodexTurnEvent.model_validate({**event, 'payload': {**event['payload'], **extra}})
    if payload_name == 'CodexTurnAnswerEvent':
        assert dto.CodexTurnEvent.model_validate(event).payload.text == ' \n'


@pytest.mark.parametrize('path', ['', '.', '..', '/outside', 'a/../b', 'a/./b', 'a//b', 'a/', 'a\\b', 'x:y', 'a\nb'])
def test_sandbox_paths_never_accept_host_or_noncanonical_names(path):
    with pytest.raises(ValidationError):
        dto.CodexOperationFile.model_validate({**samples()['CodexOperationFile'], 'path': path})
    with pytest.raises(ValidationError):
        dto.CodexArtifactEntry.model_validate({**samples()['CodexArtifactEntry'], 'logical_path': path})


@pytest.mark.parametrize('action', ['add', 'update', 'delete'])
def test_file_change_requires_actual_complete_before_after_pairs(action):
    value = samples()['CodexFileChange']
    value.update(action=action, before_sha256=None if action == 'add' else HASH,
                 before_size=None if action == 'add' else 0,
                 after_sha256=None if action == 'delete' else HASH,
                 after_size=None if action == 'delete' else 2)
    dto.CodexFileChange.model_validate(value)
    for field in ('before_sha256', 'after_sha256', 'before_size', 'after_size'):
        bad = deepcopy(value)
        bad[field] = (HASH if field.endswith('sha256') else 2) if bad[field] is None else None
        with pytest.raises(ValidationError):
            dto.CodexFileChange.model_validate(bad)


def test_approval_does_not_upgrade_decision_ack_to_execution_or_unsupported_grant():
    value = samples()['GenericApprovalView']
    value.update(decision='approve_once', revision=2, decided_at=NOW)
    assert dto.GenericApprovalView.model_validate(value).execution == 'not_started'
    for change in ({'operation': samples()['CodexDeniedOperation']}, {'execution': 'started'},
                   {'result_sha256': HASH}, {'decided_at': None}, {'revision': 1}):
        with pytest.raises(ValidationError):
            dto.GenericApprovalView.model_validate({**value, **change})
    value.update(revision=4, execution='completed', started_at=NOW, finished_at=LATER, result_sha256=HASH)
    assert dto.GenericApprovalView.model_validate(value).execution == 'completed'


def test_original_acks_are_not_current_views_or_rewritten_by_later_state():
    original = b'{"id":"session_one","revision":2,"status":"ready","capabilities":{"approvals":false,"interrupt":false,"artifacts":false},"adapter_version":"synthetic-v1"}'
    ack = bootstrap.CodexSessionCreateAck.model_validate(json.loads(original))
    before = canonical_bytes(ack)
    current = {**ack.model_dump(), 'revision': 5, 'active_turn_id': 'turn_one',
               'capabilities': {'approvals': True, 'interrupt': True, 'artifacts': True}}
    dto.CodexCurrentSessionView.model_validate(current)
    with pytest.raises(ValidationError):
        bootstrap.CodexSessionCreateAck.model_validate({k: v for k, v in current.items() if k != 'active_turn_id'})
    with pytest.raises(ValidationError):
        bootstrap.CodexSessionView.model_validate(current)
    assert canonical_bytes(ack) == before
    assert json.loads(original) == ack.model_dump()
    for change in ({'revision': 1}, {'revision': 2}, {'status': 'unknown'}):
        with pytest.raises(ValidationError):
            dto.CodexCurrentSessionView.model_validate({**current, **change})
    grant = samples()['CodexConsentCreateAck']
    grant_bytes = canonical_bytes(dto.CodexConsentCreateAck.model_validate(grant))
    now = {**samples()['CodexConsentView'], 'revision': 2, 'status': 'revoked', 'revoked_at': LATER}
    dto.CodexConsentView.model_validate(now)
    assert canonical_bytes(dto.CodexConsentCreateAck.model_validate(grant)) == grant_bytes


def test_manifest_hash_order_and_totals_are_bound_without_granting_import_of_unknown():
    manifest = samples()['CodexArtifactManifest']
    manifest['entries'].append({**manifest['entries'][0], 'artifact_id': 'artifact_two', 'logical_path': 'results/second.md'})
    manifest['total_bytes'] = 4
    view = {'manifest': manifest, 'manifest_sha256': sha256_bytes(canonical_bytes(manifest))}
    dto.CodexArtifactManifestView.model_validate(view)
    reordered = deepcopy(view)
    reordered['manifest']['entries'].reverse()
    with pytest.raises(ValidationError):
        dto.CodexArtifactManifestView.model_validate(reordered)
    # Unknown may be retained for diagnosis; the owner must reject import.
    manifest['source_outcome'] = 'unknown'
    dto.CodexArtifactManifest.model_validate(manifest)
    with pytest.raises(ValidationError):
        dto.CodexArtifactImportWrite.model_validate({'turn_id': 'turn_one', 'artifact_ids': [],
                                                     'expected_manifest_sha256': HASH})
    for name, field in [('CodexArtifactImportWrite', 'artifact_ids'), ('CodexFileOperation', 'files'),
                        ('CodexCommandOperation', 'read_files'), ('CodexTurnPage', 'items')]:
        value = samples()[name]
        value[field].append(deepcopy(value[field][0]))
        with pytest.raises(ValidationError):
            getattr(dto, name).model_validate(value)


@pytest.mark.parametrize('raw', ['{"turn_id":"one","turn_id":"two","expected_session_revision":2}',
                                '{"turn_id":"one","expected_session_revision":NaN}',
                                '{"turn_id":"one","expected_session_revision":Infinity}'])
def test_raw_json_seam_does_not_discard_duplicate_or_nonfinite_values(raw):
    with pytest.raises(ValueError):
        dto.parse_codex_turn(dto.CodexInterruptWrite, raw)


def test_generated_contract_seam_has_resolvable_closed_unions_without_any_or_routes():
    artifacts = codex_turn_artifacts({'source': 'PRODUCT_DESIGN.md', 'spec_version': '3.0.15', 'spec_sha256': HASH})
    schemas = json.loads(artifacts['codex-turn-schemas.json'])['schemas']
    assert set(samples()) == set(MODEL_NAMES)
    for name, schema in schemas.items():
        jsonschema.Draft202012Validator.check_schema(schema)
        if name in samples():
            jsonschema.validate(samples()[name], schema)
        for definition in [schema, *schema.get('$defs', {}).values()]:
            if definition.get('type') == 'object':
                assert definition['additionalProperties'] is False
                assert set(definition['required']) == set(definition['properties'])
    for name, value in [('CodexTurnEventPayload', samples()['CodexTurnAnswerEvent']),
                        ('CodexOperation', samples()['CodexCommandOperation'])]:
        jsonschema.validate(value, schemas[name])
        assert 'oneOf' in schemas[name] and 'discriminator' in schemas[name]
    types = artifacts['codex-turn-types.ts']
    assert 'export type CodexTurnEventPayload =' in types
    assert 'export type CodexOperation =' in types
    non_literals = re.sub(r'"(?:[^"\\]|\\.)*"', '"literal"', types)
    assert re.search(r'\b(any|unknown)\b', non_literals) is None
    assert 'export type SafeCode =' in types
    assert 'EndpointKey' not in types
