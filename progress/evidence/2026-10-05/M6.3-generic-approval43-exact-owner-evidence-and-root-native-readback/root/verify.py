"""Pure exact-candidate/source verification. Does not execute product tests."""
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

base = Path('$HOME/.cache/learning-workbench-acceptance')
owner = base / 'm63-generic-approval-safe-decline-evidence-oct05'
source = base / 'm63-generic-approval-safe-decline-oct05'
head = '43c70d660d98904903bd607a4661b3b95710293e'
baseline = '412abe09c519104d9dbd2b360eed3ff4f897f829'
out = Path(__file__).parent
sha = lambda b: hashlib.sha256(b).hexdigest()
sys.path.insert(0, str(base / 'm62-public-safe-oct02/scripts'))
from check_publication import inspect

def git(*argv):
    return subprocess.check_output(['git', *argv], cwd=source)

assert git('rev-parse', 'HEAD').decode().strip() == head
assert not git('status', '--porcelain')
seals = {
    'REPORT.md': 'fa5251c1b44b2681fde0af87efe8fad68583fd1c3db17ea0135da25e97bbe621',
    'PUBLIC_CANDIDATES.json': 'fa623e04c79b6b910a073e64d0e7d6b3ebc9fa28b0309344a3f72906f705d029',
    'PACKAGE_SEAL.json': 'ecac858f5d588ef5c90ac997b4970daf2451e4c98fb84933b651df01ea634e3d',
}
for name, digest in seals.items():
    assert sha((owner / name).read_bytes()) == digest, name
allow = json.loads((owner / 'PUBLIC_CANDIDATES.json').read_text())
entries = allow['entries']
assert len(entries) == 93
verified = []
for e in entries:
    n = e['candidate_path']
    assert not Path(n).is_absolute() and '..' not in Path(n).parts
    data = (owner / 'safe-candidates' / n).read_bytes()
    assert sha(data) == e['candidate_sha256'] and len(data) == e['candidate_bytes'], n
    assert not inspect('progress/' + n, data), n
    verified.append({'path': n, 'sha256': sha(data), 'bytes': len(data)})

before = json.loads((owner / 'safe-candidates/native/final-positive/before.json').read_text())
after = json.loads((owner / 'safe-candidates/native/final-positive/after.json').read_text())
terminal = json.loads((owner / 'safe-candidates/native/final-positive/terminal-source.json').read_text())
assert before == after == terminal and before['head'] == head
files = {}
for row in git('ls-tree', '-rz', head).split(b'\0'):
    if not row:
        continue
    meta, raw_path = row.split(b'\t', 1)
    name = raw_path.decode()
    if name.startswith('progress/'):
        continue
    mode, kind, oid = meta.decode().split(' ')
    data = (source / name).read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == oid
    files[name] = {'mode': mode, 'type': kind, 'git_blob': oid, 'sha256': sha(data), 'bytes': len(data)}
assert len(files) == 1522 and files == before['files']
owned = git('diff', '--name-only', baseline, head).decode().splitlines()
binding = json.loads((owner / 'safe-candidates/summary/FINAL_BINDING.json').read_text())
assert len(owned) == 11 and sorted(owned) == sorted(binding['owner_delta_paths'])
for n in ['native.mjs', 'controlled_api.py', 'run.py']:
    assert (owner / 'safe-candidates/native/counter-red' / n).read_bytes() == (owner / 'safe-candidates/native/counter-green' / n).read_bytes()
test = 'apps/web/src/features/codex/CodexApprovalsPanel.test.tsx'
red = git('show', '29fcdd0ac2bc86ee21afa54ef966073f226b70c6:' + test)
green = git('show', '11a7099d75d866f7e84fb5bafdd431c5058eb2c1:' + test)
assert red == green and sha(red) == '89c2082821d5ecc41c9124ec6866413e8f1e5c4ee908c3098d02b211670aa73c'
images = [e for e in verified if e['path'].endswith('.png')]
assert len(images) == 10
report = {
    'status': 'PURE_SOURCE_EXACT_CANDIDATES_AND_ROOT_VISUAL_READBACK_PASS',
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_sha': head, 'review_base': baseline,
    'spec_sha256': sha((source / 'PRODUCT_DESIGN.md').read_bytes()),
    'owner_seals': seals, 'complete_inputs': len(files), 'owned_paths': owned,
    'explicit_candidates': verified, 'same_counter_harness_bytes': True,
    'same_complete_component_RED_GREEN_bytes': True,
    'root_visual': {'individually_viewed': images, 'assessment': 'Synthetic operation/ACK and original versus fixed pending safe-decline controls at1440/390. No horizontal page/dialog overflow visible. Screenshots are viewport portions; complete command/ACK is supported by DOM/IndexedDB assertions, not whole-panel screenshot coverage.'},
    'new_product_tests_executed': False,
    'native_scope': 'Owned actual403 counter and positive loopback Chrome tests only; synthetic protocol requests/pure literal operations. Actual remote Provider/CLI/physical tool NOT_RUN. Complete native412 is a separate original132PASS1FAIL, not passed by these scoped tests.',
    'original_failed_evidence_rewritten': False,
    'publication': 'PRIVATE_PREPARED_ONLY',
}
(out / 'READBACK.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'candidates': len(verified), 'inputs': len(files), 'readback_sha256': sha((out / 'READBACK.json').read_bytes())}))
