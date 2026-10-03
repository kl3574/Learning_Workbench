"""Read-only verification/derivation from captured CI originals; never invokes GitHub."""
from pathlib import Path
import base64
import hashlib
import json
import re
import sys

BASE = Path(__file__).resolve().parent
HEAD = '507ac58b17e4a68b4e0f852cc6a64b535cf3235c'
MERGE = 'f74cd7a8f81a8b51abf06ae12fb62a51da3bb99d'
RUNS = {'push': 36368224612, 'pull_request': 36368226913}
CHECKOUTS = {'push': HEAD, 'pull_request': MERGE}
EXPECTED_JOBS = {'backend', 'frontend', 'integration', 'browser', 'spec-contracts', 'security-publication'}
PACKAGES = {'bubblewrap': '0.11.1-1ubuntu0.3', 'apparmor': '5.0.2-0ubuntu1~26.04.1',
            'libapparmor1:amd64': '5.0.2-0ubuntu1~26.04.1', 'libseccomp2:amd64': '2.6.0-2ubuntu5'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    label = sys.argv[1]
    output = BASE / (label + '-audit.json')
    assert not output.exists(), 'audit evidence must not be overwritten'
    captures = []
    for path in sorted(BASE.rglob('*.receipt.json')):
        receipt = json.loads(path.read_text())
        if 'stdout_file' not in receipt:
            continue  # earlier acquisition receipts use a different schema, retained separately
        raw = (BASE / receipt['stdout_file']).read_bytes()
        assert digest(raw) == receipt['stdout_sha256']
        assert len(raw) == receipt['stdout_bytes']
        stderr = path.with_name(path.name.removesuffix('.receipt.json') + '.stderr').read_bytes()
        assert digest(stderr) == receipt['stderr_sha256']
        assert receipt['reader_sha256'] == digest((BASE / 'readback.py').read_bytes())
        assert receipt['exit_code'] == 0, 'acquisition failure is not a complete original log'
        captures.append(path.relative_to(BASE).as_posix())
    commits = {}
    for event, sha in CHECKOUTS.items():
        commit = json.loads((BASE / 'source' / (event + '-actual-commit.json')).read_text())
        assert commit['sha'] == sha
        commits[event] = {'sha': sha, 'tree': commit['tree']['sha'], 'parents': [p['sha'] for p in commit['parents']]}
        source = json.loads((BASE / 'source' / (event + '-workflow-api.json')).read_text())
        workflow = (BASE / 'source' / ('workflow-' + event + '.yml')).read_bytes()
        assert base64.b64decode(source['content']) == workflow
        assert hashlib.sha1(b'blob ' + str(len(workflow)).encode() + b'\0' + workflow).hexdigest() == source['sha']
        assert workflow.count(b'bubblewrap=0.11.1-1ubuntu0.3') == 3
    assert commits['push']['tree'] == commits['pull_request']['tree']
    assert HEAD in commits['pull_request']['parents']
    events = {}
    for event, identifier in RUNS.items():
        run = json.loads((BASE / f'{label}-{event}-run.json').read_text())
        jobs = json.loads((BASE / f'{label}-{event}-jobs.json').read_text())['jobs']
        assert run['id'] == identifier and run['head_sha'] == HEAD and run['event'] == event and run['run_attempt'] == 1
        assert {j['name'] for j in jobs} == EXPECTED_JOBS and len(jobs) == 6
        facts = []
        for job in jobs:
            assert job['head_sha'] == HEAD
            fact = {'job_id': job['id'], 'job': job['name'], 'status': job['status'], 'conclusion': job['conclusion'],
                    'started_at': job['started_at'], 'completed_at': job['completed_at'],
                    'steps': [{'name': s['name'], 'status': s['status'], 'conclusion': s['conclusion']} for s in job['steps']]}
            if job['status'] == 'completed':
                path = BASE / 'logs' / f"{event}-{job['name']}-{job['id']}.log"
                lines = path.read_text().splitlines()
                fact['log_path'], fact['log_sha256'] = path.relative_to(BASE).as_posix(), digest(path.read_bytes())
                pins, summaries, packages = [], [], {}
                for index, line in enumerate(lines):
                    clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', line)
                    if 'git log -1 --format=%H' in line:
                        checkout = lines[index + 1].split()[-1]
                        assert checkout == CHECKOUTS[event]
                        pins.append({'line': index + 2, 'sha': checkout})
                    for package, version in PACKAGES.items():
                        if package + '\t' in line:
                            assert line.endswith(package + '\t' + version)
                            packages[package] = {'version': version, 'line': index + 1}
                    if (re.search(r'\b\d+ passed(?:,| in | \()', clean)
                            or re.search(r'\b(?:Tests|Test Files)\s+\d+ passed', clean)
                            or '"status": "PASS"' in clean
                            or 'Success: no issues found' in clean or 'All checks passed!' in clean
                            or 'staged/tracked files' in clean):
                        summaries.append({'line': index + 1, 'text': clean})
                assert len(pins) == 1
                fact['checkout'], fact['summaries'], fact['installed'] = pins[0], summaries, packages
                if job['name'] in {'backend', 'integration', 'browser'}:
                    assert set(packages) == set(PACKAGES)
            facts.append(fact)
        events[event] = {'run_id': identifier, 'url': run['html_url'], 'run_attempt': run['run_attempt'],
                         'status': run['status'], 'conclusion': run['conclusion'], 'head_sha': HEAD, 'jobs': facts}
    result = {'label': label, 'verified_capture_receipts': captures, 'actual_commits': commits, 'runs': events,
              'reader_sha256': digest(Path(__file__).read_bytes()),
              'scope': 'Original API/log hash and source/checkout/installed-package readback; no local product tests or reruns.'}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'events': {k: {'status': v['status'], 'conclusion': v['conclusion']} for k, v in events.items()},
                      'capture_count': len(captures), 'audit_file': output.name, 'audit_sha256': digest(output.read_bytes())}))

if __name__ == '__main__':
    main()
