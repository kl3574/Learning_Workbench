import datetime
import hashlib
import json
import subprocess
from pathlib import Path

O = Path(__file__).parent
H = '4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f'
repo = 'repos/kl3574/Learning_Workbench/'
assert not (O / 'READBACK.json').exists()
sha = lambda b: hashlib.sha256(b).hexdigest()
records = []
for run_id in [37200168176, 37200167062]:
    pair = []
    for label, suffix in [('run', ''), ('jobs', '/jobs?per_page=100')]:
        args = ['gh', 'api', repo + 'actions/runs/' + str(run_id) + suffix]
        p = subprocess.run(args, capture_output=True)
        (O / f'{run_id}-{label}.raw.json').write_bytes(p.stdout)
        (O / f'{run_id}-{label}.stderr').write_bytes(p.stderr)
        assert p.returncode == 0
        pair.append(json.loads(p.stdout))
    run, jobs = pair
    assert run['head_sha'] == H and run['path'] == '.github/workflows/ci.yml'
    assert len(jobs['jobs']) == jobs['total_count'] == 6
    records.append({k: run[k] for k in ['id', 'event', 'head_sha', 'path', 'status',
                                        'conclusion', 'created_at', 'updated_at']})
    records[-1]['jobs'] = [{k: j[k] for k in ['id', 'name', 'status', 'conclusion',
                                             'started_at', 'completed_at']}
                           for j in jobs['jobs']]
report = {'status': 'EXACT_4B_CI_METADATA_READBACK',
          'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'source_head': H, 'runs': records,
          'all_terminal': all(r['status'] == 'completed' for r in records),
          'boundary': 'Actual exact-head workflow/job metadata only. No raw job logs downloaded or checkout/tree/artifact validation in this receipt. Does not establish local3265, whole M6.3, numeric, real provider or academic acceptance. No source mutation.'}
(O / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'all_terminal': report['all_terminal'],
                  'runs': [{'id': r['id'], 'status': r['status'], 'conclusion': r['conclusion'],
                            'jobs': [(j['name'], j['status'], j['conclusion']) for j in r['jobs']]}
                           for r in records],
                  'receipt_sha256': sha((O / 'READBACK.json').read_bytes())}))
