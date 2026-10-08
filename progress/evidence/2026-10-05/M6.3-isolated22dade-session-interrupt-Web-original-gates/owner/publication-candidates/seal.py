"""Explicit UI evidence admission; no tests, remote writes or private recursion."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

root = Path('${HOME}/.cache/learning-workbench-acceptance/m63-session-interrupt-ui-oct05')
evidence = Path(__file__).parent
seal = evidence / 'seal-22dade'
assert not seal.exists()
seal.mkdir()
candidate = seal / 'publication-candidates'
candidate.mkdir()
final = '22dade7996f13634202250ef5e1c05dc976214a5'
base = '35aebd3039241abb3393300affd593f4826a4a0c'
red = 'af20b3fe90228d8f522b050a13084785eaa98af8'
green = '68420d379b69c0368305adab057432d21c1e56fb'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
assert git('rev-parse', 'HEAD').decode().strip() == final
assert not git('status', '--porcelain')
stages = [
    'focused-original-red', 'focused-baseline-original-tests', 'focused-baseline-admitted',
    'focused-baseline-private-temporary', 'focused-original-green', 'strict-first',
    'focused-final-components', 'strict-final', 'diff-final', 'full-web', 'build-final',
]
expected_heads = [red, red, red, red, green, green, final, final, final, final, final]
expected_exits = [1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0]
entries = []
def admit(raw, relative):
    data = raw.read_bytes()
    converted = data.replace(b'${HOME}', b'${HOME}')
    # Emit counts only, never matched content. All admitted files are fixed local test evidence.
    assert not re.search(rb'(?i)sk-[a-z0-9]{16,}|gh[pousr]_[a-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----', converted)
    target = candidate / relative
    assert not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(converted)
    assert target.read_bytes() == converted
    entries.append({'candidate_path': relative, 'raw_path': str(raw), 'raw_sha256': sha(data),
                    'sha256': sha(converted), 'bytes': len(converted), 'transformation': 'exact ${HOME} prefix to ${HOME} only'})
maps = []
summary = []
for stage, expected, expected_exit in zip(stages, expected_heads, expected_exits, strict=True):
    folder = evidence / stage
    receipt = json.loads((folder / 'receipt.json').read_text())
    log = (folder / 'run.log').read_bytes()
    assert receipt['head'] == expected and receipt['exit_code'] == expected_exit
    assert receipt['log_sha256'] == sha(log)
    before = json.loads((folder / 'before.json').read_text())
    after = json.loads((folder / 'after.json').read_text())
    assert before == after and len(before) == 1525
    assert receipt['before_after_git_exact'] and all(v['git_exact'] for v in before.values())
    maps.extend([(expected, before), (expected, after)])
    for name in ('receipt.json', 'before.json', 'after.json'):
        admit(folder / name, stage + '/' + name)
    if stage == 'focused-baseline-private-temporary':
        lines = log.decode().splitlines()
        bounded = {'status': 'ACTUAL_4_FAILED_1_FILE', 'raw_log_sha256': sha(log),
                   'raw_log_bytes': len(log), 'raw_log_publication': 'EXCLUDED_PRIVATE_SYNTHETIC_DOM',
                   'failure_names': [line.strip() for line in lines if line.strip().startswith('FAIL ')],
                   'common_failure': 'Missing explicit interrupt button: 明确中断会话回合 turn_test',
                   'counts': [line.strip() for line in lines if line.strip().startswith(('Test Files', 'Tests '))],
                   'head': expected, 'original_raw_retained': True}
        dump(seal / 'original-four-failure-bounded-summary.json', bounded)
        admit(seal / 'original-four-failure-bounded-summary.json', stage + '/bounded-failure-summary.json')
    else:
        admit(folder / 'run.log', stage + '/run.log')
    summary.append({'stage': stage, 'head': expected, 'exit_code': expected_exit,
                    'start': receipt['started_utc'], 'end': receipt['ended_utc'], 'log_sha256': sha(log),
                    'test_status': ('NOT_COLLECTED_TOOLCHAIN_FAILURE' if stage in stages[:3] else
                                    'ACTUAL_4_FAIL' if stage == stages[3] else
                                    'ACTUAL_2_TYPESCRIPT_ERRORS' if stage == 'strict-first' else 'PASS'),
                    'historical_runner_sha256': 'NOT_CAPTURED_BY_ORIGINAL_RECEIPT',
                    'complete_engineering_inputs': len(before), 'before_after_git_exact': True})
for name in ('run.py', 'TOOLCHAIN_SETUP.json', 'TOOLCHAIN_LAYOUT_FIX.json'):
    admit(evidence / name, name)

# Rebind every retained source map to its historical Git tree/object, without checkout changes.
blob_values = {}
bindings = 0
for head, values in maps:
    tree = {}
    for raw in filter(None, git('ls-tree', '-r', '-z', head).split(b'\0')):
        info, name = raw.split(b'\t', 1)
        mode, kind, blob = info.decode().split()
        name = name.decode()
        if name.startswith('progress/'):
            continue
        tree[name] = (mode, kind, blob)
    assert set(tree) == set(values)
    for name, value in values.items():
        assert (value['mode'], value['type'], value['git_blob']) == tree[name]
        prior = blob_values.setdefault(value['git_blob'], (value['size'], value['sha256']))
        assert prior == (value['size'], value['sha256'])
        bindings += 1
input_data = ''.join(blob + '\n' for blob in blob_values).encode()
objects = subprocess.run(['git', 'cat-file', '--batch'], cwd=root, input=input_data, stdout=subprocess.PIPE, check=True).stdout
offset = 0
for blob, (size, digest) in blob_values.items():
    end = objects.index(b'\n', offset)
    actual, kind, length = objects[offset:end].decode().split()
    assert actual == blob and kind == 'blob' and int(length) == size
    body = objects[end + 1:end + 1 + size]
    assert sha(body) == digest and objects[end + 1 + size:end + 2 + size] == b'\n'
    offset = end + 2 + size
assert offset == len(objects)
component = 'apps/web/src/features/codex/CodexTurnInterruptPanel.test.tsx'
red_component = git('show', red + ':' + component)
green_component = git('show', green + ':' + component)
assert red_component == green_component
final_map = maps[-1][1]
assert all(sha((root / path).read_bytes()) == value['sha256'] for path, value in final_map.items())
assert not git('status', '--porcelain')
dump(seal / 'STAGE_READBACK.json', {
    'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'base': base, 'final': final,
    'stages': summary, 'retained_maps': len(maps), 'map_bindings': bindings,
    'distinct_git_blobs': len(blob_values), 'all_historical_maps_git_bound': True,
    'same_complete_component_file_red_green': {'red': red, 'green': green, 'sha256': sha(red_component),
       'final_component_modified': red_component != git('show', final + ':' + component)},
    'current_runner_sha256': sha((evidence / 'run.py').read_bytes()),
    'historical_runner_hash_not_reconstructed': True, 'final_live_source_exact_clean': True,
    'external_model_calls_by_this_sealer': 0, 'original_public35ae_ci': 'BROWSER_FAIL_RETAINED',
    'whole_m63_acceptance': 'NOT_ACCEPTED', 'full_native_22dade': 'RUNNING_SEPARATE_PACKET',
})
admit(seal / 'STAGE_READBACK.json', 'STAGE_READBACK.json')
report = '''# Session interrupt UI — fixed 22dade evidence\n\nBase 35aebd; final 22dade. Eight Web source/test paths only; specification/backend/config/lock unchanged. Explicit interruption uses the existing session endpoint, original CAS/body/key and actor-bound durable journal. Historical ACK remains distinct from fresh current-session/control GET. No implicit POST on reload, no rebuild of 412 commands, other actor commands remain read-only.\n\nFirst three attempted baseline stages failed before tests collected (toolchain/module/temp transform); these are not product RED. Fourth baseline actually failed four missing-button tests. The complete component test bytes at af20 and 684 are identical, then those original four passed. First strict check actually failed two TypeScript diagnostics; final22 repairs callback narrowing and unused helper and adds negative tests. Final component/wire/journal selection: 127 passed / four files. Complete Web: 1421 passed / 167 files. Strict/diff/build exit0. Original large-chunk build advisory retained.\n\nAll 11 stages retain original receipts and both complete 1525-input maps. Each historical map is bound to mode/type/Git object/size/SHA, and final live source is exact and clean. Original four-failure raw synthetic DOM is private; only failure names/counts and its unchanged raw SHA are admitted. The current runner hash does not prove the historical runner bytes: original receipts did not capture runner SHA, and it changed to use private TMPDIR after early attempts. Do not retroactively infer it.\n\nSeparate bounded real Chrome validation and complete native run have separate packets. This packet does not prove real Provider/model/physical Broker/numeric isolation, CI firstReview root cause, whole M6.3, or M7. Both public35ae original browser CI failures remain FAIL. No model calls, push, merge, or release by this sealer.\n'''
(seal / 'REPORT.md').write_text(report)
admit(seal / 'REPORT.md', 'REPORT.md')
admit(Path(__file__), 'seal.py')
dump(seal / 'SAFE_CANDIDATES.json', {'version': 1, 'source': final,
    'candidate_base': str(candidate), 'files': entries, 'excluded': ['raw four-failure synthetic DOM',
    'private-temporary', 'dependency copies', 'dist', 'DB', 'browser profiles', 'any unlisted files']})
dump(seal / 'READBACK.json', {'source': final, 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'candidate_count': len(entries), 'safe_candidates_sha256': sha((seal / 'SAFE_CANDIDATES.json').read_bytes()),
    'all_explicit_candidates_readback_exact': True, 'git_map_bindings': bindings,
    'scope': 'Ordinary synthetic UI evidence only, no new tests or remote/model actions'})
print(json.dumps({'candidates': len(entries), 'bindings': bindings, 'blobs': len(blob_values),
    'safe_sha256': sha((seal / 'SAFE_CANDIDATES.json').read_bytes()), 'readback_sha256': sha((seal / 'READBACK.json').read_bytes())}))
