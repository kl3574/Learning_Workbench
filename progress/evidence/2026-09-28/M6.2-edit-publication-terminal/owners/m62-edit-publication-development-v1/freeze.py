"""Verify captured bytes against immutable Git; never rerun product commands."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / 'm62-edit-publication-active'
BASE = 'e58abaaf4baa5b06d27bd1db1f06c8a13c1c730a'
FINAL = '17ff439c3b7e6fce704fcc8ec2afbbb607079a0e'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, path
    else:
        path.write_bytes(raw)


def dump(path, value):
    write(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def tree(commit):
    entries = {}
    for row in git('ls-tree', '-r', '-z', commit).split(b'\0'):
        if not row:
            continue
        header, name = row.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        name = name.decode()
        if name.startswith('progress/'):
            continue
        assert kind == 'blob'
        entries[name] = (mode, oid)
    oids = sorted({oid for _, oid in entries.values()})
    output = subprocess.check_output(['git', 'cat-file', '--batch'], input=('\n'.join(oids) + '\n').encode(), cwd=ROOT)
    pos, raw_blobs = 0, {}
    for oid in oids:
        end = output.index(b'\n', pos)
        actual, kind, size = output[pos:end].decode().split()
        size = int(size)
        assert actual == oid and kind == 'blob'
        pos = end + 1
        raw = output[pos:pos + size]
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == oid
        raw_blobs[oid] = raw
        pos += size + 1
    assert pos == len(output)
    return {name: {'bytes': len(raw_blobs[oid]), 'sha256': sha(raw_blobs[oid]),
                   'git_blob': oid, 'mode': mode, 'raw': raw_blobs[oid]}
            for name, (mode, oid) in entries.items()}


def inventory(value):
    return {p: {'bytes': d['bytes'], 'sha256': d['sha256']} for p, d in value.items()}


def difference(left, right):
    return {p: {'captured': left.get(p), 'git': right.get(p)}
            for p in sorted(set(left) | set(right)) if left.get(p) != right.get(p)}


def prepare():
    assert git('rev-parse', 'HEAD').decode().strip() == FINAL
    assert git('status', '--porcelain=v1') == b''
    final = tree(FINAL)
    for path, data in final.items():
        assert (ROOT / path).read_bytes() == data['raw'], path
    changed = git('diff', '--name-only', BASE, FINAL).decode().splitlines()
    assert len(changed) == 14
    for path in changed:
        write(HERE / 'final-source' / path, final[path]['raw'])
    write(HERE / 'implementation.diff', git('diff', '--binary', BASE, FINAL))
    write(HERE / 'source-na-test-only.diff', git('diff', '7ab80860c09a68a29b068c834244ddf3d62bdd45', FINAL))
    pins = {path: {k: v for k, v in data.items() if k != 'raw'} for path, data in final.items()}
    spec = final['PRODUCT_DESIGN.md']['sha256']
    assert sha(Path('<LOCAL_HOME>/Desktop/learning/PRODUCT_DESIGN.md').read_bytes()) == spec
    dump(HERE / 'final-source-pins.json', {'base_commit': BASE, 'fixed_commit': FINAL,
         'spec_sha256': spec, 'engineering_input_count': len(final), 'changed_paths': changed,
         'worktree_matches_actual_git': True, 'clean_index_and_worktree': True, 'files': pins})
    return final


if __name__ == '__main__':
    import sys
    final = prepare()
    if '--final' not in sys.argv:
        print(json.dumps({'fixed_commit': FINAL, 'engineering_inputs': len(final), 'changed_paths': 14}))
        raise SystemExit(0)
    rows, heads = [], {FINAL: inventory(final)}
    pool = HERE / 'source-pool'
    for path in pool.iterdir():
        assert path.is_file() and sha(path.read_bytes()) == path.name
    stages = sorted(p for p in HERE.iterdir() if p.is_dir() and p.name[:2].isdigit())
    for stage in stages:
        receipt = json.loads((stage / 'receipt.json').read_bytes())
        log = (stage / 'run.log').read_bytes()
        assert len(log) == receipt['log_bytes'] and sha(log) == receipt['log_sha256']
        assert receipt['driver_sha256'] == sha((HERE / 'run.py').read_bytes())
        before = json.loads((stage / 'inputs-before.json').read_bytes())
        after = json.loads((stage / 'inputs-after.json').read_bytes())
        assert before == after and receipt['unchanged']
        assert len(before) == receipt['input_count_before'] == receipt['input_count_after']
        for path, item in before.items():
            raw = (pool / item['sha256']).read_bytes()
            assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], (stage.name, path)
        head = receipt['actual_head']
        if head not in heads:
            heads[head] = inventory(tree(head))
        rows.append({'stage': stage.name, 'receipt': receipt,
                     'input_sha256': sha((stage / 'inputs-before.json').read_bytes()),
                     'captured_source_vs_runtime_head': difference(before, heads[head]),
                     'captured_source_vs_fixed_final': difference(before, inventory(final)),
                     'complete_source_pool_and_log_verified': True})
    dump(HERE / 'run-ledger.json', rows)
    dump(HERE / 'source-verification.json', {'fixed_commit': FINAL, 'stage_count': len(rows),
         'source_pool_members': len(list(pool.iterdir())), 'all_source_pool_hashes_verified': True,
         'all_before_after_inputs_unchanged': True, 'all_original_logs_receipts_verified': True,
         'actual_git_trees': {head: len(inputs) for head, inputs in heads.items()},
         'final_equivalent_stages': [r['stage'] for r in rows if not r['captured_source_vs_fixed_final']],
         'execution_on_dirty_source_is_not_relabelled_as_final_commit': True})
    assert (HERE / 'REPORT.md').exists() and (HERE / 'TASK_RECEIPT.json').exists()
    members = {}
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.name != 'PRIVATE_MANIFEST.json':
            raw = path.read_bytes()
            members[path.relative_to(HERE).as_posix()] = {'bytes': len(raw), 'sha256': sha(raw)}
    dump(HERE / 'PRIVATE_MANIFEST.json', {'version': 1, 'private_only': True, 'members': members})
    print(json.dumps({'fixed_commit': FINAL, 'stages': len(rows), 'members': len(members),
                      'manifest_sha256': sha((HERE / 'PRIVATE_MANIFEST.json').read_bytes())}))
