"""Independent static delta and original-receipt readback; no product execution."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess

ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m63-codex-artifact-ui-owner-oct04')
EVIDENCE = ROOT.parent / 'm63-artifact-p2-repair-evidence-oct04'
PRIOR = ROOT.parent / 'm63-artifact-final-independent-review-oct04'
PACK = Path(__file__).resolve().parent
BASE = '9a2c8d032977411ce94724fd3be33403694c46e1'
HEAD = '51205a75c401911d98d54a42387fbaa43583da7f'
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'
NAMES = [
    'migrations/0035_codex_import_immutable.sql',
    'services/api/app/application/artifacts.py',
    'services/api/app/application/codex_artifacts.py',
    'services/api/app/main.py',
    'tests/integration/test_codex_artifact_repair_boundaries.py',
    'tests/integration/test_codex_import_owner.py',
]
STAGES = [
    ('migration-red-01', 1, '12 failed', '38685c693d602f98dd8b7cd953dd7844301a8dc5'),
    ('delivery-red-01', 1, '2 failed', 'e8ec33be6e8f0094ebb1136ec0c5547d2fd054f8'),
    ('delivery-red-02', 1, '4 failed', '236bf2ef8db02e65f343da1d0d6ab00dff1aab3b'),
    ('delivery-green-01', 0, '4 passed', '48346a3feb4bd05d3b5676b33125d869d5d3c372'),
    ('fixed-boundaries-01', 0, '22 passed', HEAD),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def load(path):
    return json.loads(path.read_bytes())


def tree(head):
    entries = {}
    for item in git('ls-tree', '-r', '-z', head).split(b'\0'):
        if item:
            meta, path = item.split(b'\t', 1)
            mode, kind, identifier = meta.split()
            if not path.startswith(b'progress/'):
                assert kind == b'blob'
                entries[path.decode()] = identifier.decode()
    return entries


def functions(raw):
    text = raw.decode()
    return {node.name: ast.get_source_segment(text, node) for node in ast.parse(text).body
            if isinstance(node, ast.FunctionDef)}


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == HEAD and git('status', '--porcelain') == b''
    assert git('merge-base', BASE, HEAD).decode().strip() == BASE
    assert sha((ROOT / 'PRODUCT_DESIGN.md').read_bytes()) == SPEC
    assert sha((PRIOR / 'REVIEW.md').read_bytes()) == '376a3575d33356776c869931c6d6dce0f408d6f5d758d9f8ffa61a310b6dafda'
    assert sha((PRIOR / 'READBACK.json').read_bytes()) == '711ec6529252b9ef16cb8db5d2554efd53faacf18f1a130c3b34b96f754ea592'
    changes = git('diff', '--name-only', BASE, HEAD).decode().splitlines()
    assert sorted(changes) == sorted(NAMES)
    numstat = git('diff', '--numstat', BASE, HEAD).decode().splitlines()
    assert sum(int(line.split('\t')[0]) for line in numstat) == 258
    assert sum(int(line.split('\t')[1]) for line in numstat) == 4
    source = load(EVIDENCE / 'SOURCE_BINDING.json')
    assert source['base'] == BASE and source['head'] == HEAD
    patch = git('diff', '--binary', BASE, HEAD)
    assert sha(patch) == source['patch_sha256']
    trees = {head: tree(head) for head in {BASE, HEAD, *(item[3] for item in STAGES)}}
    assert len(trees[BASE]) == 1457 and len(trees[HEAD]) == 1459
    unchanged = [name for name, identifier in trees[BASE].items() if trees[HEAD].get(name) == identifier]
    assert len(unchanged) == 1453
    old_migrations = [name for name in trees[BASE] if name.startswith('migrations/')]
    assert all(trees[HEAD][name] == trees[BASE][name] for name in old_migrations)
    ids = sorted({identifier for paths in trees.values() for identifier in paths.values()})
    process = subprocess.run(['git', 'cat-file', '--batch'], input=('\n'.join(ids)+'\n').encode(),
                             cwd=ROOT, stdout=subprocess.PIPE, check=True)
    objects, offset = {}, 0
    for identifier in ids:
        stop = process.stdout.index(b'\n', offset)
        found, kind, size = process.stdout[offset:stop].split()
        assert found.decode() == identifier and kind == b'blob'
        offset = stop + 1
        data = process.stdout[offset:offset+int(size)]
        objects[identifier] = sha(data)
        offset += int(size) + 1
    assert offset == len(process.stdout)
    for item in source['source_files']:
        assert item['path'] in NAMES and item['git_blob'] == trees[HEAD][item['path']]
        assert item['sha256'] == objects[item['git_blob']] == sha((ROOT/item['path']).read_bytes())
    stages, bindings = [], 0
    current_functions = functions((ROOT/NAMES[4]).read_bytes())
    archived_functions = {}
    for path, exit_code, summary, head in STAGES:
        folder = EVIDENCE/path
        before, after, receipt = [load(folder/name) for name in ('source-before.json', 'source-after.json', 'receipt.json')]
        assert before == after and before['head'] == head and not before['status']
        assert before['count'] == len(before['files']) == receipt['complete_nonprogress_inputs']
        assert set(item['path'] for item in before['files']) == set(trees[head])
        for item in before['files']:
            assert item['git_blob'] == item['actual_blob'] == trees[head][item['path']]
            assert item['matches_git'] and item['sha256'] == objects[item['git_blob']]
            bindings += 1
        assert receipt['source_sha'] == head and receipt['exit_code'] == exit_code and receipt['before_after_exact']
        log = (folder/'run.log').read_bytes()
        archived = (folder/'test_codex_artifact_repair_boundaries.py').read_bytes()
        assert sha(log) == receipt['log_sha256'] and sha(archived) == receipt['test_sha256']
        assert archived == git('show', head+':'+NAMES[4])
        assert summary in log.decode()
        archived_functions[path] = functions(archived)
        stages.append({'path':path, 'head':head, 'exit_code':exit_code, 'original_summary':summary,
                       'elapsed_seconds':receipt['elapsed_seconds'], 'complete_inputs':before['count'],
                       'log_sha256':receipt['log_sha256'], 'receipt_sha256':sha((folder/'receipt.json').read_bytes()),
                       'before_sha256':sha((folder/'source-before.json').read_bytes()),
                       'after_sha256':sha((folder/'source-after.json').read_bytes()),
                       'test_sha256':receipt['test_sha256']})
    for item in source['red_function_comparison']:
        exact = archived_functions[item['original_run']][item['name']] == current_functions[item['name']]
        assert exact == item['body_source_exact_final']
    assert (EVIDENCE/'fixed-boundaries-01'/'test_codex_artifact_repair_boundaries.py').read_bytes() == (ROOT/NAMES[4]).read_bytes()
    for name, identifier in trees[HEAD].items():
        assert sha((ROOT/name).read_bytes()) == objects[identifier]
    assert git('status', '--porcelain') == b'' and git('rev-parse', 'HEAD').decode().strip() == HEAD
    readback = {'recorded_at':datetime.now(timezone.utc).isoformat(), 'status':'STATIC_DELTA_AND_ORIGINAL_EVIDENCE_READBACK_PASS',
                'base':BASE, 'head':HEAD, 'sole_spec_sha256':SPEC, 'changed_paths':NAMES,
                'diff_insertions':258, 'diff_deletions':4, 'source_inputs':1459,
                'unchanged_prior_inputs':1453, 'unchanged_old_migrations':len(old_migrations),
                'original_review_unchanged':True, 'original_stages_read':stages,
                'stage_git_file_bindings':bindings, 'red_function_comparison':source['red_function_comparison'],
                'source_binding_sha256':sha((EVIDENCE/'SOURCE_BINDING.json').read_bytes()),
                'original_failure_logs_public':'HASH_ONLY', 'source_unchanged':True,
                'product_tests_executed_by_reviewer':False, 'model_cli_network_host_probes_executed':False,
                'full_combined_gates':'NOT_RUN_BY_REVIEWER; author separate gates were RUNNING at review intake',
                'whole_M6_3_acceptance':False}
    input_map = {'head':HEAD,'count':1459, 'files':[{'path':name,'git_blob':identifier,'sha256':objects[identifier]}
                                                   for name,identifier in sorted(trees[HEAD].items())]}
    for name, value in [('READBACK.json',readback),('SOURCE_INPUTS.json',input_map)]:
        target=PACK/name
        assert not target.exists()
        target.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':readback['status'], 'head':HEAD, 'changed_paths':6,'source_inputs':1459,
                      'unchanged_prior_inputs':1453,'stage_git_file_bindings':bindings,
                      'READBACK_sha256':sha((PACK/'READBACK.json').read_bytes()),
                      'product_tests_executed_by_reviewer':False},sort_keys=True))


if __name__ == '__main__':
    main()
