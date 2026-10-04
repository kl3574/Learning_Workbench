"""Controlled legacy-profile receipts, not old binary/runtime success claims."""
from pathlib import Path

import pytest

from packages.contracts.canonical import sha256_bytes, strict_json
from services.api.app.application.codex_bootstrap_models import BootstrapFreeze, BootstrapOutcome
from services.api.app.infrastructure import codex_bootstrap_runtime as module
from services.api.app.serialization import canonical_json, content_sha256
from tests.integration.test_codex_bootstrap_http import make_case, approve


class LegacyProfileFixturePort(module.LocalCodexBootstrapRuntime):
    """Synthetic execution with the real versioned frozen/receipt decoder."""
    def __init__(self, directory, version):
        super().__init__(directory, directory / 'absent-cli')
        self.version, self.current, self.calls = version, 'current', []

    def freeze(self, identifier):
        frozen = super().freeze(identifier)
        value = strict_json(frozen.description_json)
        value['version'] = self.version
        value['schemas'] = dict(module.HISTORICAL_SCHEMAS)
        # These explicit synthetic facts exist only in this named test port.
        value['binary'] = {'path': '/synthetic/non-executed-cli', **value['expected_binary']}
        value['platform']['landlock_abi'] = 3
        if self.version.endswith('-v1'):
            value['launcher'] = str(Path(module.__file__).with_name('codex_probe_isolation.py'))
            value.pop('launcher_source_utf8')
            value['resources'].pop('parent_death')
        return BootstrapFreeze.model_validate({**frozen.model_dump(), 'available': True,
            'description_json': canonical_json(value), 'scope': {**frozen.scope.model_dump(),
            'bootstrap_profile_sha256': content_sha256(value)}})

    def validity(self, frozen):
        self.validate_frozen(frozen)
        return self.current

    def execute(self, frozen, permit_id):
        self.calls.append(permit_id)
        value = strict_json(frozen.description_json)
        cwd = str(Path(value['broker_root']) / 'workspace')
        thread = {'cliVersion': '0.160.0', 'createdAt': 0, 'cwd': cwd, 'ephemeral': False,
            'id': 'synthetic-legacy-thread', 'modelProvider': 'openai', 'preview': '', 'projectId': None,
            'sessionId': 'synthetic-legacy-session', 'source': 'appServer', 'status': {'type': 'idle'},
            'turns': [], 'updatedAt': 0}
        result = {'approvalPolicy': 'never', 'approvalsReviewer': 'user', 'cwd': cwd, 'model': 'gpt-5.4',
            'modelProvider': 'openai', 'sandbox': {'type': 'readOnly', 'networkAccess': False}, 'thread': thread}
        receipt = canonical_json({'version': 'codex-bootstrap-receipt-v1', 'permit_id': permit_id,
            'profile_sha256': frozen.scope.bootstrap_profile_sha256,
            'frames_sha256': sha256_bytes(''.join(value['request_frames_utf8']).encode()),
            'initialized': {'codexHome': str(Path(value['broker_root']) / 'home'), 'platformFamily': 'unix',
                            'platformOs': 'linux', 'userAgent': 'codex_cli_rs/0.160.0'}, 'result': result})
        outcome = BootstrapOutcome(status='ready', thread_id=thread['id'], receipt_json=receipt,
                                   error_code=None, thread_start_attempted=True)
        self.validate_outcome(frozen, permit_id, outcome)
        return outcome


@pytest.mark.parametrize('version', ['codex-local-control-profile-v1', 'codex-local-control-profile-v2'])
def test_legacy_success_receipt_and_original_ack_remain_readable_when_current_profile_changes(tmp_path, monkeypatch, version):
    def no_process(*args, **kwargs):
        pytest.fail('controlled legacy receipt test attempted to execute a CLI')
    monkeypatch.setattr(module.subprocess, 'Popen', no_process)
    runtime = LegacyProfileFixturePort(tmp_path, version)
    case = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    original, _, body = approve(case, 'legacy-finished')
    response = case.post('sessions', body, 'legacy-create')
    assert response.status_code == 201
    pending, _, pending_body = approve(case, 'legacy-unused-grant')
    runtime.current = 'changed'
    before = case.dump()
    original_bytes = response.content
    replay = case.post('sessions', body, 'legacy-create')
    assert replay.status_code == 201 and replay.content == original_bytes
    prepared = case.get('session-preparations/' + original['id'])
    session = case.get('sessions/' + response.json()['id'])
    assert prepared.json()['status'] == 'consumed' and session.json()['status'] == 'ready'
    assert case.get('session-preparations/' + pending['id']).json()['validity'] == 'changed'
    assert case.post('sessions', pending_body, 'must-not-consume-old-grant').status_code == 409
    assert len(runtime.calls) == 1 and case.dump() == before
