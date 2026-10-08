import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

B = Path('$HOME/.cache/learning-workbench-acceptance')
E = B / 'm63-turn-contract-dto-evidence-oct04'
R = B / 'm63-turn-contract-dto-oct04'
O = Path(__file__).parent
sha = lambda data: hashlib.sha256(data).hexdigest()

def check(path, facts):
    data = path.read_bytes()
    assert sha(data) == facts['sha256'] and len(data) == facts['bytes'], str(path)
    return data

raw = json.loads((E / 'RAW_MANIFEST.json').read_text())
assert raw['count'] == len(raw['files']) == 42
for name, facts in raw['files'].items():
    check(E / name, facts)
safe = json.loads((E / 'SAFE_SHARE.json').read_text())
assert safe['count'] == len(safe['entries']) == 43
scanner_spec = importlib.util.spec_from_file_location('scanner', B / 'm62-public-safe-oct02/scripts/check_publication.py')
scanner = importlib.util.module_from_spec(scanner_spec)
scanner_spec.loader.exec_module(scanner)
for entry in safe['entries']:
    original = check(E / entry['raw_path'], entry['raw'])
    candidate = check(E / entry['candidate_path'], entry['candidate'])
    assert candidate == original.replace(b'$HOME', b'$HOME')
    assert not scanner.inspect('progress/evidence/turn-dto/' + entry['raw_path'], candidate)
outer = json.loads((E / 'PUBLIC_OUTER_ALLOWLIST.json').read_text())['files']
assert len(outer) == 4
for name, facts in outer.items():
    check(E / name, facts)
stages = []
for prefix, head, expected_count in [('', '760af1e44c5447f60ba53248fbdd694ee25c774d', 456),
    ('fixed-8da88ed8/', '8da88ed890a25ee9ed6753fb6b4599625e449bf8', 342)]:
    before = json.loads((E / (prefix + 'inputs-before.json')).read_text())
    after = json.loads((E / (prefix + 'inputs-after.json')).read_text())
    assert before == after and before['head'] == head and before['count'] == len(before['files']) == 1393
    tree = {}
    for entry in subprocess.check_output(['git', 'ls-tree', '-rz', '--full-tree', head], cwd=R).split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        name = name.decode()
        if not name.startswith('progress/'):
            tree[name] = metadata.split()[2].decode()
    assert set(tree) == set(before['files'])
    with subprocess.Popen(['git', 'cat-file', '--batch'], cwd=R,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        for name, facts in before['files'].items():
            assert facts['git_blob'] == tree[name]
            process.stdin.write((tree[name] + '\n').encode())
            process.stdin.flush()
            oid, kind, length = process.stdout.readline().strip().split()
            data = process.stdout.read(int(length))
            assert process.stdout.read(1) == b'\n' and kind == b'blob'
            assert oid.decode() == tree[name] and sha(data) == facts['sha256'] and len(data) == facts['bytes']
        process.stdin.close()
        assert process.wait() == 0
    gates = json.loads((E / (prefix + 'gate-results.json')).read_text())
    assert gates['terminal'] and gates['head'] == head and gates['all_pass'] and gates['engineering_inputs_unchanged']
    assert all(gate['exit_code'] == 0 for gate in gates['gates'])
    focused = (E / (prefix + '01-focused.log')).read_text()
    assert str(expected_count) + ' passed' in focused
    stages.append({'head': head, 'complete_git_inputs': 1393, 'contracts': expected_count,
        'all_declared_gates_exit0': True, 'original760_not_accepted_due_to_p2': prefix == ''})
preserved = json.loads((E / 'OLD_CONTRACT_PRESERVATION.json').read_text())
for path, facts in preserved['files'].items():
    original = subprocess.check_output(['git', 'show', preserved['base'] + ':' + path], cwd=R)
    current = subprocess.check_output(['git', 'show', preserved['head'] + ':' + path], cwd=R)
    assert current == original and sha(current) == facts['sha256'] and len(current) == facts['bytes']
assert json.loads((E / 'RAW_SCAN.json').read_text())['status'] == 'FAIL'
assert json.loads((E / 'CANDIDATE_SCAN.json').read_text())['findings'] == []
receipt = {'status': 'ROOT_EXPLICIT_DTO_EVIDENCE_READBACK_PASS', 'raw_files': 42,
    'safe_files': 43, 'outer_files': 4, 'stages': stages,
    'old_contract_exact_git_files': len(preserved['files']),
    'transform': 'Only exact personal home prefix replacement; raw scanner FAIL retained.',
    'boundary': 'Read-only hashes/Git/log verification; no test rerun/CLI/model/system probe. Formal original760 is not accepted despite456 passing tests; fixed8da scope distinct. No overall M6.3 acceptance.'}
(O / 'EVIDENCE_READBACK.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False))
