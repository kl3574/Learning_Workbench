"""Read sealed evidence and fixed Git only; no application, DB or runtime execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
repo = Path(sys.argv[2]) if len(sys.argv) > 2 else root.parent / 'm63-operation-closure-fix-oct04'
def sha(value): return hashlib.sha256(value).hexdigest()
def read(path): return json.loads((root/path).read_text())
def git(*args): return subprocess.check_output(['git', *args], cwd=repo)
raw, safe, source = read('RAW_MANIFEST.json'), read('SAFE_SHARE.json'), read('SOURCE_BINDINGS.json')
assert raw['count'] == len(raw['files']) == len({item['path'] for item in raw['files']})
assert safe['count'] == len(safe['files']) == len({item['path'] for item in safe['files']})
for item in raw['files']:
    data = (root/item['path']).read_bytes()
    assert sha(data) == item['sha256'] and len(data) == item['bytes']
spec = importlib.util.spec_from_file_location('publication_scan', repo/'scripts/check_publication.py')
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)
for item in safe['files']:
    data, public = (root/item['path']).read_bytes(), (root/'safe-share'/item['path']).read_bytes()
    assert sha(data) == item['raw_sha256'] and len(data) == item['raw_bytes']
    assert public == data.replace(bytes([47,104,111,109,101,47,108,107,120]), b'$HOME')
    assert sha(public) == item['public_sha256'] and len(public) == item['public_bytes']
    assert not scanner.inspect('progress/evidence/generic/'+item['path'], public)
    assert not re.search(rb'(?i)(authorization|x-csrf-token|cookie)["\x27]?\s*[:=]\s*["\x27]?[A-Za-z0-9_+/=-]{16,}', public)
cache = {}
def blob(identifier):
    if identifier not in cache: cache[identifier] = git('cat-file', 'blob', identifier)
    return cache[identifier]
maps = []
for item in raw['files']:
    if not item['path'].endswith('/before.json'): continue
    before, after = read(item['path']), read(item['path'].replace('/before.json', '/after.json'))
    assert before['all_exact'] and not before['status']
    if item['path'].startswith('boundary-green/'):
        assert before != after and not after['all_exact'] and after['status']
        assert read('boundary-green/receipt.json')['before_equals_after'] is False
        changed = [path for path, row in after['inputs'].items() if not row['equal']]
        assert changed == ['tests/unit/test_codex_operation_closure.py']
        for path in changed:
            final = git('show', 'a93699112412c01091223de297c835d0c892e4bf:'+path)
            assert sha(final) == after['inputs'][path]['sha256']
    else:
        assert before == after
    tree = {}
    for entry in git('ls-tree', '-r', '-z', before['head']).split(b'\0'):
        if not entry: continue
        metadata, name = entry.split(b'\t'); name = name.decode()
        if not name.startswith('progress/'): tree[name] = metadata.decode().split()[2]
    assert set(tree) == set(before['inputs']) and len(tree) == before['count']
    for path, row in before['inputs'].items():
        data = blob(tree[path])
        assert row.get('git_blob', tree[path]) == tree[path] and row['equal']
        assert sha(data) == row['sha256'] == row['git_sha256'] and len(data) == row['size']
    maps.append({'stage': item['path'].split('/')[0], 'head': before['head'], 'count': before['count']})
assert git('rev-parse', source['final_head']+'^{tree}').decode().strip() == source['final_tree']
assert sha(git('show', source['final_head']+':PRODUCT_DESIGN.md')) == source['spec_sha256']
for path, row in source['changed_paths'].items():
    identifier = git('rev-parse', source['final_head']+':'+path).decode().strip()
    assert identifier == row['git_blob'] and sha(blob(identifier)) == row['sha256'] and len(blob(identifier)) == row['bytes']
for path in source['unchanged_original_paths']:
    assert git('show', source['base']+':'+path) == git('show', source['final_head']+':'+path)
for stage in ['final-related-03', 'static-final-03']:
    assert read(stage+'/before.json')['head'] == source['final_head']
    assert read(stage+'/before.json')['count'] == 1434
    receipt = read(stage+'/receipt.json')
    assert receipt.get('exit_code', 0) == 0 and all(item['exit_code'] == 0 for item in receipt.get('results', []))
assert '226 passed' in (root/'final-related-03/run.log').read_text()
for item in read('GATE_HISTORY.json')['stages']:
    receipt = read(item['stage']+'/receipt.json')
    assert receipt['head'] == item['head'] and receipt['exit_code'] == item['exit'] and receipt['before_equals_after'] == item['source_equal']
    assert sha((root/item['stage']/'run.log').read_bytes()) == item['log_sha256']
for binding in read('RED_GREEN_BINDINGS.json')['pairs']:
    original=git('show', binding['red_head']+':'+binding['path'])
    assert original==git('show',binding['green_head']+':'+binding['path'])
    assert sha(original)==binding['whole_file_sha256'] and binding['whole_file_equal']
for name in source['unchanged_original_paths'][:2]:
    assert git('show',source['request_profile_reference']+':'+name)==git('show',source['final_head']+':'+name)
if '--skip-outer' not in sys.argv and (root/'PUBLIC_OUTER_ALLOWLIST.json').exists():
    for item in read('PUBLIC_OUTER_ALLOWLIST.json')['files']:
        data = (root/item['path']).read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['bytes']
        assert not scanner.inspect('progress/evidence/generic/'+item['path'], data)
print(json.dumps({'status': 'PASS', 'raw_count': raw['count'], 'safe_count': safe['count'],
    'source_head': source['final_head'], 'fixed_maps': maps, 'scope': 'Read-only evidence and Git; no product execution.'}, indent=2))
