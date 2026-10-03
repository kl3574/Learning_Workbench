"""Read-only exact-run API/log capture. Never dispatches or reruns a workflow."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

BASE = Path(__file__).resolve().parent
REPOSITORY = 'repos/kl3574/Learning_Workbench/'
HEAD = '507ac58b17e4a68b4e0f852cc6a64b535cf3235c'
RUNS = {'push': 36368224612, 'pull_request': 36368226913}

def capture(name, endpoint, suffix='.json'):
    target = BASE / (name + suffix)
    if target.exists():
        raise RuntimeError('refusing to overwrite existing evidence')
    command = ['gh', 'api', REPOSITORY + endpoint]
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, capture_output=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result.stdout)
    error = BASE / (name + '.stderr')
    error.write_bytes(result.stderr)
    receipt = {'command': command, 'started_at': started,
        'finished_at': datetime.now(timezone.utc).isoformat(), 'exit_code': result.returncode,
        'stdout_file': target.relative_to(BASE).as_posix(), 'stdout_bytes': len(result.stdout),
        'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
        'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(),
        'reader_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (BASE / (name + '.receipt.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    if result.returncode:
        return {'capture_failed': True, 'exit_code': result.returncode, 'receipt': name + '.receipt.json'}
    return json.loads(result.stdout) if suffix == '.json' else receipt

def log_facts(path):
    lines = path.read_text().splitlines()
    facts = {'path': path.relative_to(BASE).as_posix(), 'checkout': [], 'image': [], 'installed': [], 'summaries': []}
    for index, line in enumerate(lines):
        if 'git log -1 --format=%H' in line and index + 1 < len(lines):
            following = lines[index + 1].split()[-1]
            if re.fullmatch('[0-9a-f]{40}', following):
                facts['checkout'].append({'line': index + 2, 'sha': following})
        if re.search(r'Image: ubuntu-|Image Version:|Version: 2026|Ubuntu|26\.04\.1', line) and index < 45:
            facts['image'].append({'line': index + 1, 'text': line})
        if re.search(r'\b(?:bubblewrap|apparmor|libapparmor1(?::amd64)?|libseccomp2(?::amd64)?)\t', line):
            facts['installed'].append({'line': index + 1, 'text': line})
        if (re.search(r'\b\d+ passed(?:,| in )', line) and not line.lstrip().startswith('Run ')
                or 'Test Files ' in line or re.search(r'\bTests\s+\d+ passed', line)
                or 'Success: no issues found' in line or 'All checks passed!' in line
                or 'scanned ' in line and 'staged/tracked files' in line
                or '"status": "PASS"' in line):
            facts['summaries'].append({'line': index + 1, 'text': line})
    return facts

def main():
    label = sys.argv[1]
    requests = [(event, kind, f'actions/runs/{identifier}' + ('/jobs?per_page=100' if kind == 'jobs' else ''))
                for event, identifier in RUNS.items() for kind in ('run', 'jobs')]
    def get(item):
        event, kind, endpoint = item
        return event, kind, capture(f'{label}-{event}-{kind}', endpoint)
    retrieved = list(ThreadPoolExecutor(4).map(get, requests))
    views = {}
    for event, kind, value in retrieved:
        if value.get('capture_failed'):
            raise RuntimeError('API capture failed; inspect original receipt')
        if kind == 'run':
            assert value['head_sha'] == HEAD and value['id'] == RUNS[event] and value['event'] == event
        views.setdefault(event, {})[kind] = value
    downloads = []
    for event, view in views.items():
        for job in view['jobs']['jobs']:
            assert job['head_sha'] == HEAD
            name = f"logs/{event}-{job['name']}-{job['id']}"
            if job['status'] == 'completed' and not (BASE / (name + '.log')).exists():
                downloads.append((name, f"actions/jobs/{job['id']}/logs"))
    def download(item):
        return capture(item[0], item[1], '.log')
    acquired = list(ThreadPoolExecutor(4).map(download, downloads)) if downloads else []
    summary = {}
    for event, view in views.items():
        summary[event] = {'run_id': RUNS[event], 'status': view['run']['status'], 'conclusion': view['run']['conclusion'],
            'jobs': [{'id': job['id'], 'name': job['name'], 'status': job['status'], 'conclusion': job['conclusion'],
                'install': next((step['conclusion'] for step in job['steps'] if step['name'] == 'Install fixed official Ubuntu document sandbox dependencies'), None),
                'running_steps': [step['name'] for step in job['steps'] if step['status'] == 'in_progress']}
                for job in view['jobs']['jobs']]}
    facts = [log_facts(path) for path in sorted((BASE / 'logs').glob('*.log'))] if (BASE / 'logs').exists() else []
    (BASE / (label + '-summary.json')).write_text(json.dumps({'runs': summary, 'log_facts': facts,
        'new_log_acquisitions': acquired}, indent=2) + '\n')
    print(json.dumps({'runs': summary, 'captured_log_count': len(facts), 'log_facts': facts}))

if __name__ == '__main__':
    main()
