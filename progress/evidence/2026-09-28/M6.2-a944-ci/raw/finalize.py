"""Freeze local evidence only after this exact two-run observation reaches terminal state."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parent
HEAD = 'a944ebfbdb835a731393977a606db5b473846e98'
MERGE = 'fc68b39c5d17aee48768dc983ccac49ee387ebe3'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    with (BASE / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


terminal = json.loads((BASE / 'monitor-terminal.json').read_bytes())
label = terminal['terminal_poll']
assert terminal['monitor_status'] == 'completed'
if not (BASE / (label + '-audit.json')).exists():
    subprocess.run([sys.executable, str(BASE / 'audit-readback.py'), label], check=True)
audit = json.loads((BASE / (label + '-audit.json')).read_bytes())
assert audit['head'] == HEAD and audit['pr_actual_checkout'] == MERGE
assert audit['completed_logs_verified'] == 12
assert audit['apt_step_success_count'] == audit['apt_exact_package_log_count'] == 6
assert not audit['acquisition_failures']

discovery = json.loads((BASE / 'discovery.receipt.json').read_bytes())
assert discovery['exit_code'] == 0
assert sha((BASE / 'discovery.json').read_bytes()) == discovery['stdout_sha256']
assert sha((BASE / 'discovery.stderr').read_bytes()) == discovery['stderr_sha256']

job_details = []
for event, run in audit['runs'].items():
    assert run['status'] == 'completed'
    api_jobs = json.loads((BASE / (label + '-' + event + '-jobs.json')).read_bytes())['jobs']
    for job in run['jobs']:
        assert job['log_status'] == 'CAPTURED'
        assert job['checkout']['sha'] == {'push': HEAD, 'pull_request': MERGE}[event]
        numeric = []
        summaries = []
        lines = (BASE / job['log_path']).read_text(errors='replace').splitlines()
        for number, raw in enumerate(lines, 1):
            clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', raw)
            if re.search(r'\b(?:SKIPPED|ENV_NOT_READY|ENVIRONMENT_NOT_READY)\b|numeric.*(?:skip|not.ready)|sandbox.*(?:skip|not.ready)', clean, re.I):
                numeric.append({'line': number, 'text': clean})
            if re.search(r'\b\d+ (?:passed|failed|skipped)(?:,| in | \(|$)', clean) or re.search(r'\b(?:Tests|Test Files)\s+', clean):
                summaries.append({'line': number, 'text': clean})
        api_job = next(item for item in api_jobs if item['id'] == job['id'])
        job_details.append({'event': event, **job, 'scope_summaries': summaries,
                            'actual_steps': api_job['steps'],
                            'environment_or_skip_evidence': numeric})

artifact_details = []
for event in audit['runs']:
    remote = json.loads((BASE / (label + '-' + event + '-artifacts.json')).read_bytes())
    assert remote['total_count'] == len(remote['artifacts'])
    for artifact in remote['artifacts']:
        target = BASE / 'artifacts' / f"{event}-{artifact['id']}.zip"
        assert target.exists() and not artifact['expired']
        digest = sha(target.read_bytes())
        expected = artifact.get('digest')
        if expected:
            assert expected == 'sha256:' + digest
        matched = next(a for a in audit['artifacts'] if a['path'] == str(target.relative_to(BASE)))
        assert matched['acquisition_exit_code'] == 0
        artifact_details.append({'event': event, 'id': artifact['id'], 'name': artifact['name'],
                                 'bytes': target.stat().st_size, 'sha256': digest,
                                 'server_digest': expected, 'members': matched['members']})

write('FINAL_JOB_EVIDENCE.json', {'head': HEAD, 'pr_actual_checkout': MERGE,
                                 'jobs': job_details, 'artifacts': artifact_details,
                                 'warning': 'Job scopes overlap. Do not add their passing counts into a unique test total.'})
write('TASK_RECEIPT.json', {'status': 'complete', 'head': HEAD, 'pr_actual_checkout': MERGE,
                          'run_ids': {k: v['run_id'] for k, v in audit['runs'].items()},
                          'conclusions': terminal['pipeline_conclusions'],
                          'actual_job_logs_verified': 12, 'apt_exact_installations': 6,
                          'failure_archives': len(artifact_details),
                          'run_attempts': 1, 'rerun_or_dispatch': False,
                          'remote_methods': ['GET'], 'product_tests_run_locally': False,
                          'source_or_progress_modified': False,
                          'local_derivation_error': 'local-audit-attempt01-error.json; original ZIP unchanged, misplaced audit preserved, extraction restored and byte-verified from ZIP.',
                          'scope': 'Actual CI runs for a944 only; excludes isolated comparison 84a and every earlier head.'})
print(json.dumps({'terminal_poll': label, 'jobs': 12, 'artifacts': len(artifact_details),
                  'conclusions': terminal['pipeline_conclusions']}))
