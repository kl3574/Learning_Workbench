from tests.integration.test_codex_artifact_manifest import execute, manifest_path, consent_case, base_consent_case
from services.api.app.infrastructure import codex_answer_materializer
__all__ = ['consent_case', 'base_consent_case']


def test_current_scan_policy_change_does_not_rewrite_original_manifest_or_ack(consent_case, monkeypatch):
    case, sid, prep, _, body, ack = execute(consent_case)
    manifest = case.get(manifest_path(sid, prep))
    control = case.get('turns/'+prep['turn_id'])
    before = case.dump()
    monkeypatch.setitem(codex_answer_materializer.SCAN_PROFILE, 'content_checks', 'future-policy-v2')
    assert case.get(manifest_path(sid, prep)).content == manifest.content
    assert case.get('turns/'+prep['turn_id']).content == control.content
    assert case.post(f'sessions/{sid}/turns', body, 'start').content == ack.content
    assert case.dump() == before
    assert len(case.app.state.synthetic_transport_calls) == 1
