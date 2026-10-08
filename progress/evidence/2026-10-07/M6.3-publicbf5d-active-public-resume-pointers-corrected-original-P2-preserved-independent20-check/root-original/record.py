from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import stat
import subprocess

O = Path(__file__).resolve().parent
B = O.parent
R = B / 'm62-public-safe-oct02'
HEAD = 'bf5d2df4e7ee5156993169cdd9610fa014bdae4f'
ANCHOR = '101cee47d8e746dddac81fb6e8829069fcabff09'
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def safe(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False).replace('$HOME', '$HOME').replace('$RUNNER_HOME', '$RUNNER_HOME'))

def write(name, obj):
    (O / name).write_text(json.dumps(safe(obj), ensure_ascii=False, indent=2) + '\n')

def source():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip() == HEAD
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', HEAD], cwd=R)
    checked = 0
    for item in tree.split(b'\0'):
        if not item:
            continue
        meta, relative = item.split(b'\t', 1)
        path = relative.decode()
        if path.startswith('progress/'):
            continue
        mode, kind, blob = meta.decode().split()
        assert kind == 'blob', path
        p = R / path
        assert not p.is_symlink(), path
        raw = p.read_bytes()
        actual_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        actual_mode = '100755' if p.stat().st_mode & stat.S_IXUSR else '100644'
        assert (actual_mode, actual_blob) == (mode, blob), path
        checked += 1
    assert checked == 1564, checked
    assert sha((R / 'PRODUCT_DESIGN.md').read_bytes()) == SPEC
    assert sha(Path('$HOME/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()) == SPEC
    return {'source_head': HEAD, 'all_nonprogress_inputs': checked, 'live_Git_blob_mode_exact': True, 'spec_sha256': SPEC}

before_source = source()
write('SOURCE-BEFORE.json', before_source)
sp = importlib.util.spec_from_file_location('root_helper', B / 'm63-public079a008-progress-record-oct07/package-helper.py')
h = importlib.util.module_from_spec(sp)
sp.loader.exec_module(h)
d = 'm63-publicbf5d-two-completed-spec-job-original-logs-oct07'
p = B / d
readback = json.loads((p / 'READBACK.json').read_bytes())
rows = json.loads((p / 'SAFE-SELECTED-LINES.json').read_bytes())
assert readback['selected_original_jobs'] == 2 and len(rows) == 6
assert {r['job_id'] for r in rows} == {112915059851, 112915083822}
for row in rows:
    raw = (p / row['original_file']).read_bytes()
    assert sha(raw) == row['original_sha256']
    assert raw.decode().splitlines()[row['line_number'] - 1] == row['text_original']
names = ['read-two-spec.py', 'run-recorded.py', 'SOURCE-SNAPSHOT.json', 'READBACK.json', 'SAFE-SELECTED-LINES.json', 'root-command.json', 'root-receipt.json', 'root.stdout', 'root.stderr']
for job in readback['jobs']:
    n = str(job['job_id'])
    receipt = json.loads((p / (n + '-receipt.json')).read_bytes())
    raw = (p / (n + '.stdout')).read_bytes()
    err = (p / (n + '.stderr')).read_bytes()
    assert receipt['actual_exit'] == 0
    assert len(raw) == receipt['stdout_bytes'] == job['raw_log_bytes']
    assert sha(raw) == receipt['stdout_sha256'] == job['raw_log_sha256']
    assert len(err) == receipt['stderr_bytes'] == 0 and sha(err) == receipt['stderr_sha256']
    names.extend([n + '-command.json', n + '-receipt.json', n + '.stderr'])
assert json.loads((p / 'root-receipt.json').read_bytes())['actual_exit'] == 0
packet = h.package('M6.3-publicbf5d-two-original-spec-jobs962PASS-safe-sixline-byte-bound', [('original-safe', d, names)], safe({'source_head': HEAD, 'per_event': [{'event': 'push', 'job': 112915059851, 'passed': 962, 'warnings': 2, 'seconds': 652.30}, {'event': 'pull_request', 'job': 112915083822, 'passed': 962, 'warnings': 2, 'seconds': 678.08}], 'selected_original_lines_byte_bound': 6, 'checkout': 'pushbf5d / PR268208; full Git tree equality has separate readback', 'raw_full_logs': 'PRIVATE_NOT_COPIED', 'CI_execution_inputs_before_after': 'NOT_CAPTURED', 'no_rerun_cancel_dispatch': True, 'M6_3': 'NOT_ACCEPTED', 'actual_model_requests_by_this_reader': 0}))

s = h.read_state()
t = next(x for x in s['tasks'] if x['id'] == 'M6.3')
c = t['current_local_checkpoint']
ck = s['checkpoint']
selected_c = ['public_head', 'remote_source_push', 'current_public_originalCI']
selected_ck = ['reason', 'resume_base_code_commit', 'working_tree', 'documentary_head_at_actual_sourcepush']
before = {'state_sha256': sha((R / 'progress/state.json').read_bytes()), 'CURRENT_sha256': sha((R / 'progress/CURRENT.md').read_bytes()), 'task_current': {k: c.get(k) for k in selected_c}, 'checkpoint': {k: ck.get(k) for k in selected_ck}}
write('BEFORE-ACTIVE-RESUME.json', before)
assert c['public_head'] == '079a008cf88b37e4517cb391503a1e7393ccf374'
assert ck['publication_head'] == HEAD and ck['local_resume_engineering_anchor'] == ANCHOR
assert 'previous_public079_resume_pointers' not in c
c['previous_public079_resume_pointers'] = {k: c.get(k) for k in selected_c}
ck['previous_public079_resume_pointer_record'] = {k: ck.get(k) for k in selected_ck}
watch = B / 'm63-ci-publicbf5d-original-observation-oct07'
latest = json.loads((watch / 'LATEST.json').read_bytes())
raw = (watch / latest['snapshot']).read_bytes()
assert sha(raw) == latest['sha256']
snapshot = json.loads(raw)
assert snapshot['source_head'] == HEAD and not snapshot['read_errors']
assert {e['id'] for e in snapshot['actual_events']} == {37657156244, 37657163285}
assert all(e['head_sha'] == HEAD and e['run_attempt'] == 1 for e in snapshot['actual_events'])
write('ACTUAL-CI-SNAPSHOT.json', snapshot)
c['public_head'] = HEAD
c['remote_source_push'] = {'status': 'ACTUAL_ORDINARY_SOURCEPUSH_WITH_SEPARATE_PURE_HEAD_TREE_CONTINUATION', 'head': HEAD, 'runtime_anchor': ANCHOR, 'actual_normal_commit_push_exit': [0, 0], 'initial_wrapper_exit': 3, 'initial_PR_mismatch_cause': 'NOT_ESTABLISHED; original preserved; no second push', 'pure_readback_wrapper_exit': 0, 'no_merge_release_deploy': True, 'evidence': 'progress/evidence/2026-10-07/M6.3-publicbf5d-normal-commit-push-original-immediate-PR-mismatch-and-pure-head-tree-continuation/REPORT.json'}
c['current_public_originalCI'] = snapshot
t['previous_publicbf_ci_metadata_before_resume_correction'] = t['current_public_ci']
t['current_public_ci'] = snapshot
c['fresh_public_spec_original_CI'] = {'source': HEAD, 'per_event': [{'event': 'push', 'job': 112915059851, 'passed': 962, 'warnings': 2, 'seconds': 652.30}, {'event': 'pull_request', 'job': 112915083822, 'passed': 962, 'warnings': 2, 'seconds': 678.08}], 'evidence': packet}
ck['reason'] = 'Actual publicbf normal sourcepush and separate branch/PR/tree readback; fixed101 full local gates terminal; two originalbf CI observed without rerun; old079 failures and first push wrapper3 preserved; wholeM63 NOT_ACCEPTED'
ck['resume_base_code_commit'] = HEAD
ck['documentary_head_at_actual_sourcepush'] = HEAD
ck['working_tree'] = 'Canonical HEADbf; all1564 nonprogress blobs/modes/bytes exactbf; uncommitted postpush work consists of finite progress records and regenerated CURRENT/state only. Engineering gate anchor101; no sourcepush during original CI; user checkout untouched.'
s['verification']['ci'] = 'Publicbf originalpush37657156244 andPR37657163285 attempt1; actual statuses at bound snapshot below. Per-event backend1114P3warn, Web1421P167files, spec962P2warn and security23933 from original logs; browser/integration counts not inferred. Old079 bothFAIL retained; wholeM63 NOT_ACCEPTED.'
s['verification']['m6_3_publicbf_spec_original_and_resume_correction'] = {'metadata_snapshot': latest, 'actual_events': [{'id': e['id'], 'event': e['event'], 'status': e['status'], 'conclusion': e['conclusion'], 'jobs': [{'name': j['name'], 'status': j['status'], 'conclusion': j['conclusion']} for j in e['jobs']]} for e in snapshot['actual_events']], 'spec_original_evidence': packet, 'old079_records': 'Explicit previous snapshots preserved', 'M6_3': 'NOT_ACCEPTED', 'M7': 'todo'}
if packet not in t['evidence_paths']:
    t['evidence_paths'].append(packet)
h.save(s)
after_source = source()
assert after_source == before_source
write('SOURCE-AFTER.json', after_source)
after = {'state_sha256': sha((R / 'progress/state.json').read_bytes()), 'CURRENT_sha256': sha((R / 'progress/CURRENT.md').read_bytes()), 'task_current': {k: c.get(k) for k in selected_c}, 'checkpoint': {k: ck.get(k) for k in selected_ck}}
write('AFTER-ACTIVE-RESUME.json', after)
for file in ['progress/state.json', 'progress/CURRENT.md']:
    assert not h.inspect(file, (R / file).read_bytes())
write('ROOT-RECEIPT.json', {'actual_source_before_after_exact': True, 'source': before_source, 'original_spec_safe_lines_byte_bound': 6, 'packet': packet, 'metadata_snapshot': latest, 'originals_preserved': True, 'source_push_merge_release_deploy': False, 'model_requests': 0, 'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
print('Two original spec logs admitted; six safe lines bound; old079 active resume pointers preserved and corrected to bf. Source unchanged; no CI restart or model request.')
