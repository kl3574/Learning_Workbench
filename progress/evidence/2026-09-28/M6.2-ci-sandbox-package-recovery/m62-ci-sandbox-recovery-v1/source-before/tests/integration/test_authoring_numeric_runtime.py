"""Actual approved-input isolation, not a configuration-only sandbox assertion."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from services.api.app.infrastructure.authoring_numeric_runtime import NumericRuntime, NumericRuntimeError


def test_preview_reads_and_freezes_real_runtime_without_spawning(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("preview/check must not start subprocesses")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    runtime = NumericRuntime()
    profile = runtime.prepare()
    assert profile.evaluator_version == 'finite-arithmetic-v1'
    assert profile.wall_seconds == 5
    assert profile.runtime_manifest_sha256 == runtime.manifest_sha256()
    runtime.check(profile)


def _job(runtime):
    from services.api.app.application.authoring_models import NumericJobInput, numeric_operation_sha256
    from services.api.app.authoring_dto import NumericPlan, AuthoringCandidate
    profile = runtime.prepare()
    candidate = AuthoringCandidate(draft_id='draft_numeric', draft_revision=1, entity='block', candidate_sha256='a' * 64)
    plan = NumericPlan.model_validate({'version': 'finite-arithmetic-v1', 'seed': None, 'variables': [], 'assertions': [
        {'id': 'check_nine', 'expression': '(2 * 3 ** 2) / 2', 'expected': 9.0, 'atol': 0.0, 'rtol': 0.0, 'unit': 'J'}]})
    operation = numeric_operation_sha256('workspace_numeric', 'check_numeric', candidate, plan, profile)
    return NumericJobInput(version='authoring-numeric-job-v1', workspace_id='workspace_numeric', job_id='job_numeric',
        check_id='check_numeric', operation_sha256=operation, candidate=candidate, plan=plan, runtime=profile)


def test_actual_isolated_calculator_returns_real_value_and_output_hash():
    runtime = NumericRuntime()
    execution = runtime.run_checked(_job(runtime), lambda: False)
    result = execution.result
    known_host_denial = (result.outcome == 'environment_unavailable'
        and execution.stderr == b'bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted\n'
        and Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip() == '1')
    if known_host_denial:
        assert result.verdict == 'BLOCKED'
        assert not result.assertions
        pytest.skip('BLOCKED_ENVIRONMENT: real sealed runtime did not execute the calculator; original FAIL retained')
    assert result.outcome == 'passed', execution.stderr
    assert result.exit_code == 0
    assert result.started_at is not None
    assert result.output_sha256 is not None
    assert result.assertions[0].actual == 9.0


def test_manifest_is_full_canonical_and_contains_no_personal_paths():
    runtime = NumericRuntime()
    profile = runtime.prepare()
    document = runtime.manifest_document()
    value = json.loads(document)
    assert hashlib.sha256(document).hexdigest() == profile.runtime_manifest_sha256
    paths = {item['path'] for item in value['members']}
    assert {'runtime/bin/python3.12', 'supervisor/bwrap', 'supervisor/prlimit', 'runtime/loader',
            'runtime/lib/python312.zip', 'entry.py', 'evaluator/authoring_numeric.py',
            'manifest/runner.py', 'manifest/config.json', 'pre-exec.bpf', 'post-exec.bpf'} <= paths
    assert any(path.startswith('stdlib/encodings/') for path in paths)
    assert any(path.startswith('runtime/lib/libc.so') for path in paths)
    assert all(not path.startswith('/') and '..' not in Path(path).parts for path in paths)
    assert b'/home/' not in document


def test_changed_or_symlink_entry_invalidates_the_original_runtime(tmp_path):
    original = NumericRuntime().entry_path
    entry = tmp_path / 'entry.py'
    entry.write_bytes(original.read_bytes())
    runtime = NumericRuntime(entry_path=entry)
    profile = runtime.prepare()
    entry.write_bytes(entry.read_bytes() + b'\n# trusted deployment changed\n')
    with pytest.raises(NumericRuntimeError, match='NUMERIC_RUNTIME_CHANGED'):
        runtime.check(profile)
    entry.unlink()
    entry.symlink_to(original)
    with pytest.raises(NumericRuntimeError, match='BLOCKED_ENVIRONMENT'):
        runtime.prepare()


def test_cancelled_before_spawn_has_no_fabricated_start_exit_or_output(monkeypatch):
    runtime = NumericRuntime()
    job = _job(runtime)
    def forbidden(*args, **kwargs):
        pytest.fail('cancelled before launch must not start any process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    execution = runtime.run_checked(job, lambda: True)
    assert execution.result.outcome == 'cancelled'
    assert execution.result.started_at is None
    assert execution.result.exit_code is None
    assert execution.result.output_sha256 is None
    assert execution.stdout == execution.stderr == b''
    assert runtime.cancel() is False


def test_known_host_denial_preserves_real_failed_start_without_fallback():
    runtime = NumericRuntime()
    starts = []
    execution = runtime.run_checked(_job(runtime), lambda: False, on_started=starts.append)
    if execution.result.outcome != 'environment_unavailable':
        pytest.skip('this host did not reproduce the sealed-launch environment denial')
    assert execution.stderr == b'bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted\n'
    assert Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip() == '1'
    assert execution.result.verdict == 'BLOCKED'
    assert execution.result.assertions == []
    if execution.result.started_at is not None:
        assert starts == [execution.result.started_at]
        assert execution.result.exit_code != 0
    else:
        assert starts == []
        assert execution.result.exit_code is None
    assert execution.result.output_sha256 == (hashlib.sha256(execution.stdout).hexdigest()
        if execution.stdout and execution.output_complete else None)
    assert execution.manifest_json


def test_runtime_factory_does_not_resolve_or_read_files(monkeypatch):
    import builtins
    import os
    def forbidden(*args, **kwargs):
        pytest.fail('runtime factory must not inspect the filesystem')
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'resolve', forbidden)
        patch.setattr(os, 'open', forbidden)
        patch.setattr(builtins, 'open', forbidden)
        runtime = NumericRuntime()
        assert runtime.cancel() is False
