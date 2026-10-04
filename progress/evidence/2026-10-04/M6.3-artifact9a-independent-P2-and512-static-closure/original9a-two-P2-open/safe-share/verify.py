"""Independent readback only: Git, existing evidence, hashes; no product execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m63-artifact-import-safe-read-oct04')
PACK = Path(__file__).resolve().parent
SEAL = ROOT.parent / 'm63-turn-artifact-evidence-oct04' / 'aggregate-seal'
BASE = SEAL.parent
HEAD = '9a2c8d032977411ce94724fd3be33403694c46e1'
FIXED = '83d7b9164968e314261a3d12f5fb3fc75d2e8c6d'
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def load(path):
    return json.loads(path.read_bytes())


def tree(head):
    result = {}
    for item in git('ls-tree', '-r', '-z', head).split(b'\0'):
        if item:
            meta, path = item.split(b'\t', 1)
            if not path.startswith(b'progress/'):
                mode, kind, identifier = meta.split()
                assert kind == b'blob', path
                result[path.decode()] = identifier.decode()
    return result


def main():
    before = git('status', '--porcelain')
    assert before == b'' and git('rev-parse', 'HEAD').decode().strip() == HEAD
    assert git('merge-base', FIXED, HEAD).decode().strip() == FIXED
    assert sha((ROOT / 'PRODUCT_DESIGN.md').read_bytes()) == SPEC
    assert sha((ROOT.parent / 'm62-public-safe-oct02' / 'PRODUCT_DESIGN.md').read_bytes()) == SPEC
    source = load(SEAL / 'SOURCE.json')
    assert source['heads']['final'] == HEAD and source['sole_spec_sha256'] == SPEC
    raw, safe, outer = [load(SEAL / name) for name in ('RAW_MANIFEST.json', 'SAFE_SHARE.json', 'PUBLIC_OUTER_ALLOWLIST.json')]
    assert raw['count'] == len(raw['items']) == 124
    assert safe['count'] == len(safe['items']) == 104
    assert outer['count'] == len(outer['items']) == 4
    raw_checks = []
    for item in raw['items']:
        data = (BASE / item['path']).read_bytes()
        assert len(data) == item['size'] and sha(data) == item['sha256'], item['path']
        raw_checks.append({'path': item['path'], 'sha256': item['sha256']})
    inspect = runpy.run_path(str(ROOT / 'scripts/check_publication.py'))['inspect']
    for item in safe['items']:
        original = (BASE / item['raw_path']).read_bytes()
        candidate = (SEAL / item['candidate_path']).read_bytes()
        assert sha(original) == item['raw_sha256']
        expected = original.replace(b'$HOME', b'$HOME') if item['transform'] == 'exact_home_prefix' else original
        assert candidate == expected and sha(candidate) == item['sha256'] and len(candidate) == item['size']
        assert not inspect('progress/evidence/review/' + item['candidate_path'], candidate), item['candidate_path']
    for item in outer['items']:
        data = (SEAL / item['path']).read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['size']
        assert not inspect('progress/evidence/review/' + item['path'], data)
    trees = {stage['head']: tree(stage['head']) for stage in source['stages']}
    unique = sorted({identifier for paths in trees.values() for identifier in paths.values()})
    output = subprocess.check_output(['git', 'cat-file', '--batch'], input=('\n'.join(unique) + '\n').encode(), cwd=ROOT)
    objects, offset = {}, 0
    for identifier in unique:
        stop = output.index(b'\n', offset)
        actual, kind, size = output[offset:stop].split()
        assert actual.decode() == identifier and kind == b'blob'
        offset = stop + 1
        data = output[offset:offset + int(size)]
        objects[identifier] = (sha(data), len(data))
        offset += int(size) + 1
    assert offset == len(output)
    count, stages = 0, []
    for stage in source['stages']:
        original, final = [load(BASE / stage['path'] / name) for name in ('before.json', 'after.json')]
        assert original == final and original['head'] == stage['head'] and not original['status']
        assert original['all_exact'] and original['count'] == stage['input_count'] == len(original['inputs'])
        assert set(original['inputs']) == set(trees[stage['head']])
        for name, item in original['inputs'].items():
            digest, size = objects[trees[stage['head']][name]]
            assert item['equal'] and digest == item['sha256'] == item['git_sha256'] and size == item['size']
            count += 1
        receipt = load(BASE / stage['path'] / 'receipt.json')
        assert receipt == stage['receipt'] and receipt['head'] == stage['head']
        stages.append({'path': stage['path'], 'head': stage['head'], 'inputs': stage['input_count'],
                       'exit_code': receipt.get('exit_code'),
                       'static_exit_codes': [item['exit_code'] for item in receipt.get('results', [])]})
    final = load(BASE / 'safe-read-static-01' / 'after.json')
    assert final['count'] == 1457 and final['head'] == HEAD
    for name, item in final['inputs'].items():
        data = (ROOT / name).read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['size']
    for group in ('peer_import_exact', 'unchanged_pure_profiles'):
        for item in source[group]:
            old = source['heads']['peer_import'] if group == 'peer_import_exact' else item['base']
            original = git('show', old + ':' + item['path'])
            current = git('show', HEAD + ':' + item['path'])
            assert original == current and sha(current) == item['sha256']
    for item in source['probe_bindings']:
        data = (BASE / item['path']).read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['bytes']
    assert git('status', '--porcelain') == before and git('rev-parse', 'HEAD').decode().strip() == HEAD
    report = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'status': 'STATIC_EVIDENCE_READBACK_PASS',
              'head': HEAD, 'merge_base': FIXED, 'sole_spec_sha256': SPEC,
              'source_inputs': 1457, 'stage_pairs': len(stages), 'stage_git_file_bindings': count,
              'raw_hashes': len(raw_checks), 'safe_candidates': safe['count'], 'outer_candidates': outer['count'],
              'seal_sha256': {name: sha((SEAL / name).read_bytes()) for name in
                              ('REPORT.md', 'SOURCE.json', 'RAW_MANIFEST.json', 'SAFE_SHARE.json', 'PUBLIC_OUTER_ALLOWLIST.json', 'VERIFICATION.json')},
              'stages': stages, 'source_unchanged': True, 'product_tests_executed': False,
              'model_or_cli_or_network_executed': False, 'whole_M6_3_accepted': False,
              'private_probe_scope': 'Retained explicit probe bytes checked; they are not part of the original nonprogress Git map.'}
    target = PACK / 'READBACK.json'
    assert not target.exists()
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': report['status'], 'stage_pairs': len(stages), 'source_inputs': 1457,
                      'stage_git_file_bindings': count, 'raw_hashes': raw['count'], 'safe_candidates': safe['count'],
                      'outer_candidates': outer['count'], 'READBACK_sha256': sha(target.read_bytes()),
                      'product_tests_executed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
