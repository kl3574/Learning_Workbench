"""Integrity and exact-origin verifier; never executes saved tests or runtime probes."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(root, relative):
    name = Path(relative)
    if name.is_absolute() or '..' in name.parts or not name.parts:
        raise ValueError('unsafe relative path')
    path = root / name
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('nonregular or escaping file')
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-root', type=Path)
    parser.add_argument('--raw-home')
    args = parser.parse_args()
    if (args.raw_root is None) != (args.raw_home is None):
        parser.error('raw-root and raw-home must be supplied together')
    root = Path(__file__).resolve().parent
    obj = lambda name: json.loads(read(root, name))
    manifest = obj('manifest.json')
    assert manifest['version'] == 'independent-reviews-public-v1'
    entries = manifest['files']
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    assert not any(p.is_symlink() for p in root.rglob('*'))
    assert actual == set(entries) | {'manifest.json'}
    for name, entry in entries.items():
        data = read(root, name)
        assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], name
        assert not set(Path(name).parts) & {'probe-data', 'pytest-temp', 'sessions', 'secrets'}
        assert Path(name).suffix.lower() not in {'.db', '.sqlite', '.sqlite3', '.zip', '.har', '.key', '.pem'}
        assert not re.search(r'/home/[A-Za-z0-9_.-]+/', data.decode('utf-8')), name
    aggregate = sha(''.join(f'{entries[p]["sha256"]}  {p}\n' for p in sorted(entries)).encode())
    assert aggregate == manifest['payload_aggregate_sha256']
    origins = obj('raw-origin-map.json')
    assert origins['home_marker'] == '<HOME>' and origins['sensitive_value_redactions'] == []
    mapping = origins['files']
    lookup = {m['public_path']: m for m in mapping}
    assert len(lookup) == len(mapping)
    assert set(lookup) == set(entries) - set(manifest['generated_payload_files'])
    for item in mapping:
        data = read(root, item['public_path'])
        assert sha(data) == item['public_sha256'] and len(data) == item['public_bytes']
        assert item['sensitive_value_redactions'] == []
        if args.raw_root:
            raw = read(args.raw_root, item['raw_relative_path'])
            assert sha(raw) == item['raw_sha256'] and len(raw) == item['raw_bytes']
            assert raw.count(args.raw_home.encode()) == item['home_substitutions']
            assert raw.replace(args.raw_home.encode(), b'<HOME>') == data
    assert sum(m['home_substitutions'] for m in mapping) == origins['total_home_substitutions']
    fingerprint = lambda name: lookup[name]['raw_sha256']
    evidence = obj('backend-review/evidence-readback.json')
    inputs = {}
    for run, expected in evidence['runs'].items():
        prefix = 'backend-checks/' + run + '/'
        receipt = obj(prefix + 'receipt.json')
        before, after = obj(prefix + 'inputs-before.json'), obj(prefix + 'inputs-after.json')
        assert len(before) == len(after) == 938 and before == after
        assert len({r['path'] for r in before}) == 938
        assert receipt['before_count'] == receipt['after_count'] == 938 and receipt['input_changes'] == []
        assert receipt['exit_code'] == expected['exit_code']
        assert fingerprint(prefix + 'receipt.json') == expected['receipt_sha256']
        log_map = lookup[prefix + 'output.log']
        assert log_map['raw_sha256'] == receipt['log_sha256'] == expected['log_sha256']
        assert log_map['raw_bytes'] == receipt['log_bytes']
        assert read(root, prefix + 'output.log').decode().splitlines()[-1] == expected['log_final_line']
        inputs[run] = {r['path']: r for r in before}
    changed = sorted(p for p in inputs['green'] if inputs['green'][p]['sha256'] != inputs['red-fixture-repaired'][p]['sha256'])
    assert changed == evidence['red_to_green_content_changed_paths'] and len(changed) == 12
    fixed = obj('backend-review/review-inputs-initial.json')['files']
    assert len(fixed) == 11
    for path, values in fixed.items():
        for directory, field, run in [('before', 'before_sha256', 'red-fixture-repaired'), ('current', 'after_sha256', 'green')]:
            assert fingerprint('backend-review/' + directory + '/' + path) == values[field] == inputs[run][path]['sha256']
    saved = obj('backend-checks/source-green.json')
    assert len(saved) == 18
    for item in saved:
        assert fingerprint('backend-checks/source-green/' + item['path']) == item['sha256'] == inputs['green'][item['path']]['sha256']
    test = 'tests/integration/test_authoring_numeric_provider_history.py'
    assert fingerprint('backend-review/current/' + test) == evidence['new_test_sha256'] == inputs['green'][test]['sha256']
    assert fingerprint('backend-review/before/' + test) == inputs['red-fixture-repaired'][test]['sha256']
    def functions(prefix):
        tree = ast.parse(read(root, prefix + test))
        return {n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    before, after = functions('backend-review/before/'), functions('backend-review/current/')
    for name, unchanged in evidence['original_test_function_ast_unchanged'].items():
        assert unchanged and before[name] == after[name]
    original_manifest = obj('backend-review/manifest.json')
    for name, entry in original_manifest['files'].items():
        original = lookup['backend-review/' + name]
        assert entry['sha256'] == original['raw_sha256'] and entry['bytes'] == original['raw_bytes']
    design = obj('indexeddb-design/manifest.json')
    assert fingerprint('indexeddb-design/DESIGN.md') == design['design_sha256']
    for name, entry in design['source_files'].items():
        assert fingerprint('indexeddb-design/source-reviewed/' + name) == entry['sha256']
    frontend = obj('indexeddb-review/inputs-before.json')
    assert len(frontend['files']) == 3
    for name, entry in frontend['files'].items():
        assert fingerprint('indexeddb-design/source-reviewed/' + name) == entry['before_sha256']
        assert fingerprint('indexeddb-review/current/' + name) == entry['current_sha256']
    followup = obj('indexeddb-review/wording-followup.json')
    name = followup['file']
    original = read(root, 'indexeddb-review/current/' + name)
    updated = read(root, 'indexeddb-review/wording-followup/' + name)
    assert original.replace('当前权限或工作区已变化，未写入这次草稿。'.encode(), '权限或工作区已变化，已停止当前保存；此前提交的记录保留。'.encode()) == updated
    assert fingerprint('indexeddb-review/current/' + name) == followup['original_reviewed_sha256']
    assert fingerprint('indexeddb-review/wording-followup/' + name) == followup['followup_sha256']
    end = obj('indexeddb-review/inputs-after.json')
    assert end['head'] == frontend['head'] and end['changed_during_review'] == [name]
    for path, digest in end['files'].items():
        assert digest == (followup['followup_sha256'] if path == name else frontend['files'][path]['current_sha256'])
    scanner_path = root / 'verification/publication-scanner.py'
    spec = importlib.util.spec_from_file_location('bounded_publication_scanner', scanner_path)
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    failures = {name: errors for name in sorted(actual) if (errors := scanner.inspect(manifest['target_prefix'] + '/' + name, read(root, name)))}
    assert not failures, failures
    print(json.dumps({'verified': True, 'mode': 'public+exact-raw' if args.raw_root else 'public-only',
        'files_including_manifest': len(actual), 'original_bindings': len(mapping), 'home_substitutions': origins['total_home_substitutions'],
        'sensitive_value_redactions': 0, 'payload_aggregate_sha256': aggregate, 'manifest_sha256': sha(read(root, 'manifest.json')),
        'backend_runs_checked': 4, 'within_run_stable_input_count': 938, 'backend_green_snapshots_checked': 18,
        'frontend_review_files': 3, 'wording_only_followup_checked': True, 'copied_actual_scanner_failures': failures,
        'tests_or_probes_executed': False, 'excluded_private_state_opened': False}, indent=2))


if __name__ == '__main__':
    main()
