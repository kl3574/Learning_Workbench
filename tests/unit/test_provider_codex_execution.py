"""Pure synthetic transport tests: no processes, files, sockets or model calls."""
from dataclasses import replace

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_codex_profile import RESOURCE_VALUES
from services.api.app.codex_turn_dto import CodexFrozenOutboundSummary, CodexTurnRuntimeSummary
from services.api.app.provider_dto import MessageSummary
from tests.unit.test_provider_codex_profile import config, registry, tools, budget, messages, BOOTSTRAP


def frozen():
    selected = registry()
    profile = selected.freeze(BOOTSTRAP, tools(), config=config())
    prepared = selected.prepare(config(), profile, messages(), [], budget())
    summary = CodexFrozenOutboundSummary(version='codex-outbound-summary-v1',
        preparation_id='preparation_1', preparation_sha256='a' * 64,
        session_id='session_1', turn_id='turn_1', job_id='job_1', source_job_revision=1,
        source_input_sha256='b' * 64, provider_id=config().id, provider_revision=config().revision,
        config_sha256=config().config_sha256, adapter='codex_app_server', adapter_version=prepared.adapter_version,
        endpoint=prepared.endpoint, endpoint_policy=config().endpoint_policy, model=config().model,
        context_snapshot_id='context_1', context_snapshot_sha256='c' * 64, input_sha256='d' * 64,
        request_body_sha256=sha256_bytes(prepared.body), messages=[MessageSummary(role=value.role,
            character_count=len(value.content), content_sha256=sha256_bytes(value.content.encode())) for value in messages()],
        references=[], input_character_count=prepared.input_character_count,
        input_token_assurance=prepared.input_token_assurance, budget=budget(), tools=tools(),
        runtime=CodexTurnRuntimeSummary(profile_sha256=sha256_bytes(canonical_bytes(profile)), **RESOURCE_VALUES),
        cost_estimate=prepared.cost_estimate, created_at='2026-10-04T00:00:00Z', expires_at='2026-10-04T00:05:00Z')
    return prepared, summary, profile


def response(body, answer='冻结回答 😀', **changes):
    value = dict(version='codex-synthetic-response-v1', outcome='completed', answer=answer,
        input_tokens=len(body), output_tokens=len(answer.encode()), error_code=None)
    return canonical_bytes(value | changes)


def execution(prepared, summary, profile, **kwargs):
    from services.api.app.application.provider_codex_execution import SyntheticCodexExecution
    return SyntheticCodexExecution(prepared, summary, profile, **kwargs)


def test_production_default_does_not_call_any_transport():
    prepared, summary, profile = frozen()
    result = execution(prepared, summary, profile).run()
    assert result.outcome == 'failed'
    assert result.error_code == 'CODEX_RUNTIME_UNAVAILABLE'
    assert result.consumed_provider_calls == 0
    assert result.usage.input_tokens is None


def test_single_exact_complete_request_and_response():
    prepared, summary, profile = frozen()
    calls = []
    def transport(body, endpoint, maximum):
        calls.append((body, endpoint, maximum))
        return response(body)
    result = execution(prepared, summary, profile, transport=transport).run()
    assert calls == [(prepared.body, prepared.endpoint, summary.budget.max_output_tokens)]
    assert result.outcome == 'completed' and result.error_code is None
    assert result.output_state == 'complete' and result.answer == '冻结回答 😀'
    assert result.consumed_provider_calls == 1
    assert result.first_response_sha256 == sha256_bytes(response(prepared.body))
    assert result.first_response.outcome == 'completed'
    assert result.usage.input_tokens == len(prepared.body)
    assert result.usage.output_tokens == len(result.answer.encode())


@pytest.mark.parametrize('catch', [False, True])
@pytest.mark.parametrize('mutation', ['identical_retry', 'tool_feedback', 'redirect'])
def test_second_request_is_rejected_before_transport_even_if_peer_catches(catch, mutation):
    prepared, summary, profile = frozen()
    calls = []
    def transport(body, endpoint, maximum):
        calls.append(body)
        return response(body)
    def peer(gate):
        gate.request(prepared.body, endpoint=prepared.endpoint, max_output_tokens=100)
        body = prepared.body + b' tool feedback' if mutation == 'tool_feedback' else prepared.body
        endpoint = prepared.endpoint + '/elsewhere' if mutation == 'redirect' else prepared.endpoint
        if catch:
            with pytest.raises(ApiError) as error:
                gate.request(body, endpoint=endpoint, max_output_tokens=100)
            assert error.value.code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'
        else:
            gate.request(body, endpoint=endpoint, max_output_tokens=100)
    result = execution(prepared, summary, profile, transport=transport).run(peer)
    assert len(calls) == 1 and result.consumed_provider_calls == 1
    assert result.outcome == 'failed' and result.error_code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'
    assert result.answer == '冻结回答 😀' and result.output_state == 'partial'
    assert result.first_response_sha256 == sha256_bytes(response(prepared.body))


@pytest.mark.parametrize('part', ['body', 'endpoint', 'output'])
def test_first_request_mismatch_is_zero_transport(part):
    prepared, summary, profile = frozen()
    calls = []
    def peer(gate):
        gate.request(prepared.body + b' ' if part == 'body' else prepared.body,
            endpoint=prepared.endpoint + '/redirect' if part == 'endpoint' else prepared.endpoint,
            max_output_tokens=101 if part == 'output' else 100)
    result = execution(prepared, summary, profile, transport=lambda *args: calls.append(args)).run(peer)
    assert calls == [] and result.consumed_provider_calls == 0
    assert result.outcome == 'failed' and result.error_code == 'CODEX_BINDING_INVALID'


@pytest.mark.parametrize('code', ['CODEX_CONSENT_REVOKED', 'POLICY_DENIED', 'CODEX_INPUT_PROOF_UNAVAILABLE'])
def test_outer_recheck_rejection_preserves_safe_code_zero_calls(code):
    prepared, summary, profile = frozen()
    calls = []
    def guard():
        raise ApiError(409, code, 'private detail must not escape')
    result = execution(prepared, summary, profile, transport=lambda *args: calls.append(args)).run(before_request=guard)
    assert calls == [] and result.consumed_provider_calls == 0
    assert result.outcome == 'failed' and result.error_code == code
    assert 'private detail' not in result.model_dump_json()


def test_unknown_guard_failure_never_calls_transport():
    prepared, summary, profile = frozen()
    calls = []
    def guard():
        raise RuntimeError('private runtime detail')
    result = execution(prepared, summary, profile, transport=lambda *args: calls.append(args)).run(before_request=guard)
    assert calls == [] and result.consumed_provider_calls == 0
    assert result.outcome == 'unknown' and result.error_code == 'CODEX_OUTCOME_UNKNOWN'


def test_transport_unknown_does_not_retry_and_instance_cannot_rerun():
    prepared, summary, profile = frozen()
    calls = []
    def transport(*args):
        calls.append(args)
        raise RuntimeError('private remote exception')
    selected = execution(prepared, summary, profile, transport=transport)
    result = selected.run()
    assert len(calls) == 1 and result.consumed_provider_calls == 1
    assert result.outcome == 'unknown' and result.error_code == 'CODEX_OUTCOME_UNKNOWN'
    repeated = selected.run()
    assert len(calls) == 1 and repeated.error_code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'


@pytest.mark.parametrize('raw', [b'', b'{}', b'{"answer":"x","answer":"y"}',
    b'{"version":"redirect","location":"https://example.com"}', b'NaN'])
def test_bad_frames_fail_closed(raw):
    prepared, summary, profile = frozen()
    result = execution(prepared, summary, profile, transport=lambda *args: raw).run()
    assert result.outcome == 'failed' and result.error_code == 'CODEX_PROTOCOL_INVALID'
    assert result.answer == '' and result.first_response_sha256 is None
    assert result.consumed_provider_calls == 1


@pytest.mark.parametrize('changes,code', [({'output_tokens': 101}, 'CODEX_BUDGET_EXCEEDED'),
    ({'output_tokens': 0}, 'PROVIDER_USAGE_INCONSISTENT'),
    ({'input_tokens': 0}, 'PROVIDER_USAGE_INCONSISTENT')])
def test_budget_and_inconsistent_usage_preserve_first_typed_response(changes, code):
    prepared, summary, profile = frozen()
    raw = response(prepared.body, **changes)
    result = execution(prepared, summary, profile, transport=lambda *args: raw).run()
    assert result.outcome == 'failed' and result.error_code == code
    assert result.answer == '冻结回答 😀' and result.output_state == 'partial'
    assert result.first_response_sha256 == sha256_bytes(raw)


def test_actual_answer_over_output_cap_cannot_hide_behind_reported_usage():
    prepared, summary, profile = frozen()
    result = execution(prepared, summary, profile,
        transport=lambda body, *_: response(body, answer='x' * 101, output_tokens=0)).run()
    assert result.error_code == 'CODEX_BUDGET_EXCEEDED'
    assert result.output_state == 'partial' and len(result.answer) == 101


@pytest.mark.parametrize('when,expected_calls', [('before', 0), ('guard', 0), ('after', 1)])
def test_monotonic_wall_limit_before_and_after_call(when, expected_calls):
    prepared, summary, profile = frozen()
    now = [0.0]
    calls = []
    def peer(gate):
        if when == 'before':
            now[0] = 30.0
        gate.request(prepared.body, endpoint=prepared.endpoint, max_output_tokens=100)
    def guard():
        if when == 'guard':
            now[0] = 30.0
    def transport(body, *_):
        calls.append(body)
        now[0] = 30.0
        return response(body)
    result = execution(prepared, summary, profile, transport=transport, clock=lambda: now[0]).run(peer, before_request=guard)
    assert len(calls) == expected_calls
    assert result.error_code == 'CODEX_TIMEOUT' and result.outcome == 'failed'
    if expected_calls:
        assert result.answer == '冻结回答 😀' and result.output_state == 'partial'


@pytest.mark.parametrize('change', ['body', 'runtime', 'budget', 'assurance', 'config'])
def test_invalid_frozen_binding_stops_before_peer_and_transport(change):
    prepared, summary, profile = frozen()
    if change == 'body':
        prepared = replace(prepared, body=prepared.body + b' ')
    elif change == 'runtime':
        summary = summary.model_copy(update={'runtime': summary.runtime.model_copy(update={'profile_sha256': 'f' * 64})})
    elif change == 'budget':
        summary = summary.model_copy(update={'budget': summary.budget.model_copy(update={'max_output_tokens': 101})})
    elif change == 'assurance':
        prepared = replace(prepared, input_character_count=prepared.input_character_count + 1)
    else:
        summary = summary.model_copy(update={'provider_revision': 99})
    touched = []
    result = execution(prepared, summary, profile, transport=lambda *args: touched.append('transport')).run(
        lambda gate: touched.append('peer'))
    assert touched == [] and result.error_code == 'CODEX_BINDING_INVALID'


def test_no_request_or_peer_failure_cannot_report_completed():
    prepared, summary, profile = frozen()
    result = execution(prepared, summary, profile, transport=lambda *args: b'').run(lambda gate: None)
    assert result.outcome == 'failed' and result.error_code == 'CODEX_PROTOCOL_INVALID'
    def failing_peer(gate):
        gate.request(prepared.body, endpoint=prepared.endpoint, max_output_tokens=100)
        raise RuntimeError('not a successful controlled turn')
    result = execution(prepared, summary, profile, transport=lambda body, *_: response(body)).run(failing_peer)
    assert result.outcome == 'unknown' and result.error_code == 'CODEX_OUTCOME_UNKNOWN'
    assert result.answer == '冻结回答 😀' and result.output_state == 'partial'


def test_request_flags_and_noncanonical_frame_cannot_be_silently_extended():
    prepared, summary, profile = frozen()
    altered = strict_json(prepared.body)
    altered['retries'] = 1
    changed = replace(prepared, body=canonical_bytes(altered))
    result = execution(changed, summary, profile, transport=lambda *args: b'').run()
    assert result.error_code == 'CODEX_BINDING_INVALID'
    result = execution(prepared, summary, profile, transport=lambda body, *_: response(body) + b' ').run()
    assert result.error_code == 'CODEX_PROTOCOL_INVALID'


def test_failed_first_response_survives_a_later_caught_extra_request():
    prepared, summary, profile = frozen()
    calls = []
    def transport(body, *_):
        calls.append(body)
        return response(body, outcome='failed', error_code='CODEX_OPERATION_FAILED')
    def peer(gate):
        for _ in range(2):
            with pytest.raises(ApiError):
                gate.request(prepared.body, endpoint=prepared.endpoint, max_output_tokens=100)
    result = execution(prepared, summary, profile, transport=transport).run(peer)
    assert len(calls) == 1 and result.error_code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'
    assert result.first_response.outcome == 'failed'
    assert result.first_response.error_code == 'CODEX_OPERATION_FAILED'


def test_transport_exception_after_deadline_is_unknown_timeout_not_success():
    prepared, summary, profile = frozen()
    now = [0.0]
    def transport(*args):
        now[0] = 30.0
        raise RuntimeError('no complete response')
    result = execution(prepared, summary, profile, transport=transport, clock=lambda: now[0]).run()
    assert result.outcome == 'unknown' and result.error_code == 'CODEX_TIMEOUT'
    assert result.consumed_provider_calls == 1 and result.first_response is None


def test_retained_gate_cannot_issue_after_peer_returns_and_run_cannot_restart():
    prepared, summary, profile = frozen()
    retained, calls = [], []
    def transport(body, *_):
        calls.append(body)
        return response(body)
    def peer(gate):
        retained.append(gate)
        gate.request(prepared.body, endpoint=prepared.endpoint, max_output_tokens=100)
    selected = execution(prepared, summary, profile, transport=transport)
    assert selected.run(peer).outcome == 'completed'
    with pytest.raises(ApiError) as error:
        retained[0].request(prepared.body, endpoint=prepared.endpoint, max_output_tokens=100)
    assert error.value.code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'
    assert len(calls) == 1
    assert selected.run().error_code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'


def test_trusted_callback_reentrancy_cannot_open_two_transport_entries():
    prepared, summary, profile = frozen()
    retained, calls = [], []
    def guard():
        with pytest.raises(ApiError):
            retained[0].request(prepared.body, endpoint=prepared.endpoint, max_output_tokens=100)
    def peer(gate):
        retained.append(gate)
        gate.request(prepared.body, endpoint=prepared.endpoint, max_output_tokens=100)
    result = execution(prepared, summary, profile, transport=lambda *args: calls.append(args)).run(peer, before_request=guard)
    assert result.error_code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED' and calls == []
