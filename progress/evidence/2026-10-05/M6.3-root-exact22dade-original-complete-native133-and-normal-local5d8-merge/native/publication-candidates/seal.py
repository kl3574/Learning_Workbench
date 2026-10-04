"""Seal exact full-native text evidence; runtime bodies and generated PNG stay private."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

evidence = Path(__file__).parent
source = evidence.parent / 'm63-native-formal-22dade-owner-oct05'
canonical = evidence.parent / 'm62-public-safe-oct02'
seal = evidence / 'seal-22dade'
assert not seal.exists()
seal.mkdir()
candidate = seal / 'publication-candidates'
candidate.mkdir()
sha = lambda data: hashlib.sha256(data).hexdigest()
head = '22dade7996f13634202250ef5e1c05dc976214a5'
receipt = json.loads((evidence / 'receipt.json').read_text())
command = json.loads((evidence / 'command.json').read_text())
before = json.loads((evidence / 'inputs-before.json').read_text())
after = json.loads((evidence / 'inputs-after.json').read_text())
changes = json.loads((evidence / 'generated-output-changes.json').read_text())
assert receipt['source_sha'] == head and receipt['exit_code'] == receipt['wrapper_exit_code'] == 0
assert command['argv'] == ['make', 'test-e2e'] and command['changed_test_or_budget'] is False
assert command['runner_sha256'] == sha((evidence / 'run.py').read_bytes())
assert receipt['native_log_sha256'] == sha((evidence / 'native.log').read_bytes()) == '4c65a40f025bf0d2a350ba95ca9751f9924836d6c60b74b5d5844bbf3298a04a'
assert receipt['before_map_sha256'] == sha((evidence / 'inputs-before.json').read_bytes())
assert receipt['after_map_sha256'] == sha((evidence / 'inputs-after.json').read_bytes())
assert receipt['actual_diff_sha256'] == sha((evidence / 'actual-tracked-diff.patch').read_bytes())
assert receipt['actual_suite_summary'] == ['\n  133 passed (20.4m)']
assert before['head'] == after['head'] == head and before['count'] == after['count'] == 1525
assert before['status'] == '' and before['all_match_git'] and not after['all_match_git']
tree = {}
for entry in filter(None, subprocess.check_output(['git', 'ls-tree', '-rz', head], cwd=source).split(b'\0')):
    metadata, name = entry.split(b'\t', 1)
    mode, kind, blob = metadata.decode().split()
    name = name.decode()
    if not name.startswith('progress/'):
        tree[name] = (mode, kind, blob)
assert len(tree) == 1525
old = {v['path']: v for v in before['files']}
new = {v['path']: v for v in after['files']}
assert set(tree) == set(old) == set(new)
blobs = {}
for name, value in old.items():
    assert (value['mode'], value['type'], value['git_blob']) == tree[name]
    assert value['git_blob'] == value['actual_blob'] and value['matches_git']
    blobs.setdefault(value['git_blob'], (value['bytes'], value['sha256']))
    assert sha((source / name).read_bytes()) == new[name]['sha256']
objects = subprocess.run(['git', 'cat-file', '--batch'], cwd=source,
    input=''.join(blob + '\n' for blob in blobs).encode(), stdout=subprocess.PIPE, check=True).stdout
offset = 0
for blob, (size, digest) in blobs.items():
    end = objects.index(b'\n', offset)
    actual, kind, length = objects[offset:end].decode().split()
    assert actual == blob and kind == 'blob' and int(length) == size
    assert sha(objects[end + 1:end + 1 + size]) == digest
    offset = end + 2 + size
assert offset == len(objects)
generated = json.loads((evidence / 'generated-output-paths.json').read_text())['paths']
actual = [name for name in old if old[name] != new[name]]
assert actual == changes['actual_changed_paths'] == receipt['actual_generated_output_changes']
assert len(actual) == 5 and set(actual).issubset(set(generated)) and len(generated) == 10
assert all(old[name] == new[name] for name in old if name not in generated)
for name in generated:
    assert sha((evidence / 'generated-before' / Path(name).name).read_bytes()) == old[name]['sha256']
    assert sha((evidence / 'generated-after' / Path(name).name).read_bytes()) == new[name]['sha256']
(seal / 'SOURCE_READBACK.json').write_text(json.dumps({'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head': head, 'before_complete_git_bound': 1525, 'distinct_git_blobs': len(blobs),
    'current_after_bytes_match_original_map': True, 'unchanged_non_generated': 1515,
    'actual_generated_changes': actual, 'complete_inputs_unchanged': False,
    'generated_before_after_ten_actual_hashes_exact': True, 'no_restore_copyback': True,
    'raw_binary_diff_sha256_only': receipt['actual_diff_sha256'], 'private_runtime_admitted': False,
    'scope': 'Full original native133PASS for22dade; public35ae bothCI browserFAIL retained, realProvider/CLI/physical/wholeM6.3 NOT_ACCEPTED'}, indent=2) + '\n')
(seal / 'REPORT.md').write_text('''# Fixed 22dade — original complete native gate\n\nActual `make test-e2e` on isolated fixed22dade: 133 passed /20.4m, command and wrapper exit0. Started19:48:14.154076 UTC, finished20:08:38.880476 UTC; native logSHA4c65a40f025bf0d2a350ba95ca9751f9924836d6c60b74b5d5844bbf3298a04a. Configuration, original time limits, workers and retries unchanged. FirstReview history14.8s and second delayedReview14.3s actually passed locally. Both original public35ae browser CI132P1F remain FAIL/unique causeUNKNOWN.\n\nBefore1525 engineering inputs exactly Git-bound. After1515 nongenerated inputs unchanged; five of ten prelisted generated outputs changed, complete input equality=false. Both whole maps, generated-change metadata, command/runner and original successful log retained. All ten original generated before/after copies hash-checked, kept private with binary diff (only digest admitted); no restore/reset/copyback. Runtime DB, browser profiles, results bodies and all unlisted PNG/JSON remain private.\n\nThis is a full local browser gate, separate from bounded new interrupt Chrome evidence. It does not prove realProvider/Codex modelCLI/physicalBroker/numeric isolation/source-math-teaching quality or entireM6.3/M7. No model or remote action by this sealer.\n''')
sys.path.insert(0, str(canonical / 'scripts'))
from check_publication import inspect
names = ['run.py', 'SETUP.json', 'command.json', 'receipt.json', 'inputs-before.json', 'inputs-after.json',
    'native.log', 'generated-output-paths.json', 'generated-output-changes.json']
entries = []
for raw in [*(evidence / name for name in names), seal / 'SOURCE_READBACK.json', seal / 'REPORT.md', Path(__file__)]:
    data = raw.read_bytes()
    safe = data.replace(b'${HOME}', b'${HOME}')
    relative = raw.name
    assert not inspect('progress/' + relative, safe)
    (candidate / relative).write_bytes(safe)
    assert (candidate / relative).read_bytes() == safe
    entries.append({'candidate_path': relative, 'raw_path': str(raw), 'raw_sha256': sha(data),
        'sha256': sha(safe), 'bytes': len(safe), 'transformation': 'literal home-prefix only'})
(seal / 'SAFE_CANDIDATES.json').write_text(json.dumps({'source': head, 'candidate_base': str(candidate), 'files': entries}, indent=2) + '\n')
(seal / 'READBACK.json').write_text(json.dumps({'source': head, 'candidate_count': len(entries), 'all_sha_size_transform_exact': True,
    'git_bound_before': 1525, 'non_generated_unchanged': 1515, 'complete_unchanged': False,
    'excluded': ['runtime DB', 'all results bodies/PNG', 'binary diff', 'generated before/after PNG', 'browser profiles'],
    'source_merge_push': False, 'wholeM6_3': 'NOT_ACCEPTED'}, indent=2) + '\n')
print(json.dumps({'candidates': len(entries), 'safe_sha256': sha((seal / 'SAFE_CANDIDATES.json').read_bytes()),
    'readback_sha256': sha((seal / 'READBACK.json').read_bytes())}))
