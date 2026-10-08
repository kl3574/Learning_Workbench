"""Bounded, read-only collection of two specifically authorized CI runs."""
from pathlib import Path
import concurrent.futures
import datetime
import hashlib
import json
import re
import subprocess

O = Path(__file__).parent
SOURCE = '1a6473dadcf71623008188f465586495ab28a204'
REPO = 'repos/kl3574/Learning_Workbench/'
RUNS = [(37207897702, 'push'), (37207899600, 'pull_request')]
sha = lambda value: hashlib.sha256(value).hexdigest()


def save(name, value):
    path = O / name
    assert not path.exists(), name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def fetch(name, route, seconds=40):
    command = ['gh', 'api', REPO + route]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        result = subprocess.run(command, capture_output=True, timeout=seconds)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code = error.stdout or b'', error.stderr or b'', None
    for suffix, raw in [('.raw', stdout), ('.stderr', stderr)]:
        path = O / (name + suffix)
        assert not path.exists(), path
        path.write_bytes(raw)
    receipt = {'command': command, 'started_at': started, 'exit_code': code,
        'stdout': name + '.raw', 'stdout_sha256': sha(stdout), 'stdout_bytes': len(stdout),
        'stderr': name + '.stderr', 'stderr_sha256': sha(stderr), 'stderr_bytes': len(stderr),
        'public_candidate': False}
    save(name + '.command.json', receipt)
    return receipt, stdout


assert not (O / 'READBACK.json').exists()
requests = [(str(run), 'actions/runs/' + str(run)) for run, _ in RUNS]
requests += [(str(run) + '-jobs', 'actions/runs/' + str(run) + '/jobs?per_page=100') for run, _ in RUNS]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = dict(zip((name for name, _ in requests), pool.map(lambda pair: fetch(*pair), requests), strict=True))
report = {'source_head': SOURCE, 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'collector_sha256': sha(Path(__file__).read_bytes()), 'runs': [], 'all12jobs_terminal': False,
    'application_execution': 'NOT_RUN', 'scope': 'Exact two CI events; no source/remote mutations, no rerun or numeric execution.'}
for run, event in RUNS:
    run_receipt, run_raw = results[str(run)]
    jobs_receipt, jobs_raw = results[str(run) + '-jobs']
    entry = {'id': run, 'expected_event': event, 'run_fetch_exit': run_receipt['exit_code'],
        'jobs_fetch_exit': jobs_receipt['exit_code']}
    if run_receipt['exit_code'] == 0 and jobs_receipt['exit_code'] == 0:
        value, page = json.loads(run_raw), json.loads(jobs_raw)
        assert value['id'] == run and value['event'] == event and value['head_sha'] == SOURCE
        assert page['total_count'] == len(page['jobs']) == 6
        entry.update({key: value[key] for key in ['event', 'status', 'conclusion', 'head_sha', 'run_attempt', 'created_at', 'updated_at']})
        entry['pull_request_bindings'] = [{'number': item['number'], 'base_sha': item['base']['sha'],
            'head_sha': item['head']['sha']} for item in value['pull_requests']]
        entry['jobs'] = [{key: job[key] for key in ['id', 'name', 'status', 'conclusion', 'started_at', 'completed_at']}
            for job in page['jobs']]
        entry['metadata_sha256'] = sha(run_raw)
        entry['jobs_metadata_sha256'] = sha(jobs_raw)
    report['runs'].append(entry)
report['all12jobs_terminal'] = all(run.get('status') == 'completed' and len(run.get('jobs', [])) == 6
    and all(job['status'] == 'completed' for job in run['jobs']) for run in report['runs'])
save('METADATA_READBACK.json', report)
if not report['all12jobs_terminal']:
    report['status'] = 'CURRENT_METADATA_SNAPSHOT_NOT_ALL_TERMINAL'
    save('READBACK.json', report)
    print(json.dumps({'status': report['status'], 'runs': [{'id': r['id'], 'status': r.get('status'),
        'conclusion': r.get('conclusion'), 'job_states': [(j['name'], j['status'], j['conclusion']) for j in r.get('jobs', [])]}
        for r in report['runs']], 'sha256': sha((O / 'READBACK.json').read_bytes())}))
    raise SystemExit(0)


def log_read(item):
    run, job = item
    receipt, raw = fetch(str(run['id']) + '-job-' + str(job['id']), 'actions/jobs/' + str(job['id']) + '/logs', 45)
    result = {'run_id': run['id'], 'event': run['event'], 'job_id': job['id'], 'job_name': job['name'],
        'conclusion': job['conclusion'], 'fetch_exit': receipt['exit_code'],
        'raw_file': receipt['stdout'], 'raw_sha256': sha(raw), 'bytes': len(raw),
        'checkout_shas': [], 'test_counts': [], 'environment_skip_markers': [], 'failure_markers': []}
    if receipt['exit_code'] == 0:
        lines = raw.decode(errors='replace').splitlines()
        for index, line in enumerate(lines[:-1]):
            if '[command]' in line and 'git log -1 --format=%H' in line:
                matched = re.search(r'\b([0-9a-f]{40})\s*$', lines[index + 1])
                if matched:
                    result['checkout_shas'].append(matched.group(1))
        for index, line in enumerate(lines, 1):
            # Keep numeric outcome fragments only, never arbitrary log lines.
            if re.search(r'\b(?:passed|failed|skipped|deselected|errors?)\b', line):
                counts = re.findall(r'\b(\d+) (passed|failed|skipped|deselected|errors?)\b', line)
                if counts:
                    result['test_counts'].append({'line': index, 'counts': [{'n': int(n), 'outcome': status} for n, status in counts]})
            markers = [marker for marker in ['BLOCKED_ENVIRONMENT', 'ENVIRONMENT_UNAVAILABLE', 'SANDBOX_UNAVAILABLE',
                'Operation not permitted', 'CAPABILITY_UNSUPPORTED'] if marker in line]
            if markers:
                result['environment_skip_markers'].append({'line': index, 'markers': markers})
            if re.search(r'(?:^|\s)(FAILED|ERROR) (tests/[^\s]+)', line):
                match = re.search(r'(FAILED|ERROR) (tests/[^\s]+)', line)
                result['failure_markers'].append({'line': index, 'kind': match.group(1), 'test': match.group(2)})
    return result


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    report['logs'] = list(pool.map(log_read, [(run, job) for run in report['runs'] for job in run['jobs']]))
complete = all(row['fetch_exit'] == 0 and len(row['checkout_shas']) == 1 for row in report['logs'])
report['all12logs_collected_checkout_parsed'] = complete
report['status'] = 'TERMINAL_METADATA_LOG_COLLECTION_INCOMPLETE'
if complete:
    push = {row['checkout_shas'][0] for row in report['logs'] if row['event'] == 'push'}
    pr = {row['checkout_shas'][0] for row in report['logs'] if row['event'] == 'pull_request'}
    assert push == {SOURCE} and len(pr) == 1
    pr_sha = next(iter(pr))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        commits = list(pool.map(lambda pair: fetch(*pair), [('source-commit', 'git/commits/' + SOURCE),
            ('pr-checkout-commit', 'git/commits/' + pr_sha)]))
    report['commit_fetch_exits'] = [receipt['exit_code'] for receipt, _ in commits]
    if report['commit_fetch_exits'] == [0, 0]:
        source, merge = [json.loads(raw) for _, raw in commits]
        assert source['sha'] == SOURCE and merge['sha'] == pr_sha
        bindings = next(r for r in report['runs'] if r['event'] == 'pull_request')['pull_request_bindings']
        assert len(bindings) == 1 and bindings[0]['head_sha'] == SOURCE
        assert {p['sha'] for p in merge['parents']} == {SOURCE, bindings[0]['base_sha']}
        assert merge['tree']['sha'] == source['tree']['sha']
        report.update(status='EXACT1A_12_TERMINAL_JOBS_LOGS_AND_CHECKOUT_TREE_VERIFIED',
            push_checkout=SOURCE, pr_checkout=pr_sha, shared_tree=source['tree']['sha'],
            pr_parents=[p['sha'] for p in merge['parents']])
report['boundary'] = 'Separate push and PR outcomes; never sum duplicate gates. Environment skip is not physical numeric PASS. No artifacts or numeric execution collected here.'
save('READBACK.json', report)
print(json.dumps({'status': report['status'], 'all12jobs_terminal': report['all12jobs_terminal'],
    'logs_collected': sum(row['fetch_exit'] == 0 for row in report['logs']),
    'push_checkout': report.get('push_checkout'), 'pr_checkout': report.get('pr_checkout'),
    'shared_tree': report.get('shared_tree'), 'receipt_sha256': sha((O / 'READBACK.json').read_bytes())}))
