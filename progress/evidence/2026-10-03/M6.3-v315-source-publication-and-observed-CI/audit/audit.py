import hashlib
import importlib.util
import json
import subprocess
import time
from pathlib import Path

ROOT = Path('$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02')
OUT = Path(__file__).parent
HEAD = '69029bc1ab355efdbb6e0fdb8a86204c59cea71a'
PUBLIC_BASE = '4ecc27a883782855a6e5611d7610979e4b4b05ca'
assert not (OUT / 'receipt.json').exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)
spec = importlib.util.spec_from_file_location('publication_scanner', ROOT / 'scripts/check_publication.py')
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)
clock = time.monotonic()
inputs = {}
findings = []
with subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as batch:
    def blob(oid):
        batch.stdin.write((oid + '\n').encode()); batch.stdin.flush()
        header = batch.stdout.readline().strip().split()
        assert len(header) == 3 and header[1] == b'blob', oid
        length = int(header[2]); result = batch.stdout.read(length)
        assert len(result) == length and batch.stdout.read(1) == b'\n'
        return result
    entries = subprocess.check_output(['git', 'ls-tree', '-r', '-z', HEAD], cwd=ROOT).split(b'\0')
    tree_count = 0
    for entry in filter(None, entries):
        metadata, name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        assert kind == b'blob'
        name = name.decode(); oid = oid.decode()
        data = blob(oid)
        reasons = scanner.inspect(name, data)
        if reasons:
            findings.append({'scope': 'current_tree', 'path': name, 'object': oid, 'reasons': reasons})
        inputs['tree:' + name] = {'object': oid, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        tree_count += 1
    outgoing = subprocess.check_output(['git', 'rev-list', '--objects', HEAD, '^' + PUBLIC_BASE], cwd=ROOT, text=True).splitlines()
    outgoing_blobs = 0
    for record in outgoing:
        oid, separator, name = record.partition(' ')
        kind = subprocess.check_output(['git', 'cat-file', '-t', oid], cwd=ROOT, text=True).strip()
        if kind != 'blob':
            continue
        assert separator and name, oid
        data = blob(oid)
        reasons = scanner.inspect(name, data)
        if reasons:
            findings.append({'scope': 'outgoing_history', 'path': name, 'object': oid, 'reasons': reasons})
        inputs['outgoing:' + oid] = {'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        outgoing_blobs += 1
    batch.stdin.close(); batch.wait()
    assert batch.returncode == 0
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)
(OUT / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
receipt = {'status': 'PASS_BOUNDED_PUBLICATION_SCANNER' if not findings else 'FAIL_PUBLICATION_STOPPED',
           'head': HEAD, 'public_base': PUBLIC_BASE, 'current_tree_files': tree_count,
           'outgoing_objects': len(outgoing), 'outgoing_blobs': outgoing_blobs,
           'seconds': time.monotonic() - clock, 'findings': findings,
           'sourcepush': False,
           'boundary': 'Approved v315 normative and documentary history publication audit. Fixed50ec168 contract/unit plus structural80/54core/Ruff/Web TS PASS, actualruntime116 unchanged; ee history-only proposal addition preserves gatedinputs. Current4ecc dual fullCI successful separately. Newturn runtime/model/tool/manifest implementation in two private worktrees not integrated. Explicit raw/safe allowlists reviewed. No merge/release/deploy/model. Future commits need fresh delta admission.'}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k:v for k,v in receipt.items() if k != 'findings'}))
print('findings_count', len(findings))
raise SystemExit(0 if not findings else 1)
