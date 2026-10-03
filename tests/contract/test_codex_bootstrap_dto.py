"""Closed local-control DTOs; these tests do not start a process or a model."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from services.api.app import codex_bootstrap_dto as dto


def preparation():
    return {'id': 'prep_one', 'revision': 1, 'actor_session_id': 'actor_one', 'status': 'pending',
            'scope': {'version': 'codex-local-session-bootstrap-v1', 'sandbox_root_id': 'workspace_default',
                      'sandbox_label': '隔离控制目录', 'allowed_actions': [], 'adapter_version': 'codex-cli/0.160.0',
                      'bootstrap_profile_sha256': 'a' * 64},
            'operation_sha256': 'b' * 64, 'created_at': '2026-10-03T00:00:00Z',
            'expires_at': '2026-10-03T00:10:00Z', 'consent_id': None, 'session_id': None, 'validity': 'current'}


@pytest.mark.parametrize('field', list(preparation()))
def test_every_public_preparation_member_is_required(field):
    value = preparation()
    del value[field]
    with pytest.raises(ValidationError):
        dto.CodexBootstrapPreparationView.model_validate(value)


@pytest.mark.parametrize('field,value', [('revision', True), ('revision', 2), ('consent_id', 'consent'),
    ('session_id', 'session'), ('validity', 'closed'), ('expires_at', '2026-10-03T00:11:00Z')])
def test_preparation_state_is_bound_to_actual_revision_and_ten_minute_scope(field, value):
    sample = preparation()
    sample[field] = value
    with pytest.raises(ValidationError):
        dto.CodexBootstrapPreparationView.model_validate(sample)


@pytest.mark.parametrize('value', [['read'], ['write'], [None], (), None, {}])
def test_empty_actions_cannot_acquire_any_permission(value):
    with pytest.raises(ValidationError):
        dto.CodexBootstrapPreparationWrite.model_validate({'sandbox_root_id': 'root', 'allowed_actions': value})


@pytest.mark.parametrize('value', [True, 0, 1, 'false', None])
def test_false_product_flags_are_strict_false(value):
    sample = {'approvals': False, 'interrupt': False, 'artifacts': False}
    sample['approvals'] = value
    with pytest.raises(ValidationError):
        dto.CodexBootstrapFeatures.model_validate(sample)


@pytest.mark.parametrize('value', [' ', '\ud800', '/private/host/path', 'line\nlabel'])
def test_safe_labels_cannot_be_private_paths_or_invalid_unicode(value):
    sample = preparation()['scope']
    sample['sandbox_label'] = value
    with pytest.raises(ValidationError):
        dto.CodexBootstrapScope.model_validate(sample)


def test_closed_acks_and_views_distinguish_original_fact_from_current_state():
    original = preparation()
    assert dto.CodexBootstrapPreparationView.model_validate(original).model_dump() == original
    current = deepcopy(original)
    current.update(revision=3, status='consumed', consent_id='consent_one', session_id='codex_one', validity='closed')
    assert dto.CodexBootstrapPreparationView.model_validate(current).revision == 3
    ack = {'preparation_id': original['id'], 'revision': 2, 'actor_session_id': 'actor_one',
           'decision': 'approve_once', 'operation_sha256': original['operation_sha256'],
           'consent_id': 'consent_one', 'decided_at': '2026-10-03T00:01:00Z'}
    dto.CodexBootstrapDecisionAck.model_validate(ack)
    with pytest.raises(ValidationError):
        dto.CodexBootstrapDecisionAck.model_validate({**ack, 'decision': 'decline'})
    ready = {'id': 'codex_one', 'revision': 2, 'status': 'ready', 'adapter_version': 'codex-cli/0.160.0',
             'capabilities': {'approvals': False, 'interrupt': False, 'artifacts': False}}
    dto.CodexSessionCreateAck.model_validate(ready)
    for changed in ({'revision': True}, {'status': 'unknown'}, {'external_thread_id': 'private'}):
        with pytest.raises(ValidationError):
            dto.CodexSessionCreateAck.model_validate({**ready, **changed})
    for status in ('initializing', 'ready', 'failed', 'unknown'):
        value = {**ready, 'revision': 1 if status == 'initializing' else 2, 'status': status, 'active_turn_id': None}
        dto.CodexSessionView.model_validate(value)
        with pytest.raises(ValidationError):
            dto.CodexSessionView.model_validate({**value, 'active_turn_id': 'forbidden'})


def test_generated_types_preserve_empty_actions_and_closed_required_objects():
    from scripts.codex_bootstrap_contracts import MODEL_NAMES, codex_bootstrap_artifacts
    from scripts.schema_types import typescript_type
    assert typescript_type({'type': 'array', 'items': {'type': 'string'}, 'maxItems': 0}) == '[]'
    artifacts = codex_bootstrap_artifacts({'source': 'PRODUCT_DESIGN.md', 'spec_version': '3.0.14', 'spec_sha256': 'a' * 64})
    assert '"allowed_actions": [];' in artifacts['codex-bootstrap-types.ts']
    for name in MODEL_NAMES:
        schema = getattr(dto, name).model_json_schema()
        assert schema['additionalProperties'] is False
        assert set(schema['properties']) == set(schema['required'])
