from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
def sha(data):
    return hashlib.sha256(data).hexdigest()
def put_json(name, value):
    with (HERE / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())

receipts = []
for version, script, stdout, stderr, chunk, exit_code in [
    ('v1', 'audit_rule.py', '05-AUDIT.stdout', '05-AUDIT.stderr', 'ff714e', 1),
    ('v2', 'audit_rule_v2.py', '06-FINAL-AUDIT.stdout', '06-FINAL-AUDIT.stderr', '9b5a48', 0)
]:
    receipts.append({'version': version, 'tool': 'exec_command',
                     'actual_chunk_id': chunk, 'actual_exit_code': exit_code,
                     'shell_command': 'python3 ' + script + ' > ' + stdout + ' 2> ' + stderr,
                     'cwd': str(HERE), 'script_sha256': sha((HERE / script).read_bytes()),
                     'stdout': {'path': stdout, 'bytes': len((HERE / stdout).read_bytes()),
                                'sha256': sha((HERE / stdout).read_bytes())},
                     'stderr': {'path': stderr, 'bytes': len((HERE / stderr).read_bytes()),
                                'sha256': sha((HERE / stderr).read_bytes())},
                     'HOME_CODEX_HOME_override': False, 'product_execution': False})
put_json('07-AUDIT-COMMANDS-AND-ACTUAL-RECEIPTS.json', {'entries': receipts})
payload = sorted(str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file())
assert len(payload) == 19
assert not any(p.is_symlink() for p in HERE.rglob('*'))
assert json.loads((HERE / 'FINAL-REVIEW.json').read_bytes())['findings'] == []
entries = []
for name in payload:
    data = (HERE / name).read_bytes()
    e = {'file': name, 'bytes': len(data), 'sha256': sha(data), 'category': 'reviewer finite metadata',
         'transformation': 'none'}
    if name.startswith('safe-plan/'):
        e['source_package'] = 'm63-current101-eleventh-exact-archive-rule-plan-oct07'
        e['source_relative'] = name.removeprefix('safe-plan/')
        e['category'] = 'original immutable private rule plan metadata'
    entries.append(e)
put_json('FINITE-ALLOWLIST.json', {
    'finite_payload_count': len(entries), 'entries': entries,
    'scope': 'one proposed literal archive rule only',
    'final_admission_files': ['FINAL-REPORT.md', 'FINAL-REVIEW.json'],
    'v1_failure_and_premature_REPORT_retained': True,
    'raw_whitespace_stdout_copy': False, 'rule_applied_by_reviewer': False,
    'Standards_new_blocking': 0, 'Spec_new_blocking': 0
})
with (HERE / 'SHA256SUMS').open('xb') as stream:
    stream.write(''.join(e['sha256'] + '  ' + e['file'] + '\n' for e in entries).encode())
put_json('SEAL.json', {'payload_count': len(entries), 'sidecars': 3,
                       'FINITE_ALLOWLIST_sha256': sha((HERE / 'FINITE-ALLOWLIST.json').read_bytes()),
                       'SHA256SUMS_sha256': sha((HERE / 'SHA256SUMS').read_bytes()),
                       'proposed_attrs_sha256': '1bc2eeba8343bd4b536e98ce2ba6a7b6e244fadbc4e46099ee5c7b7484723990',
                       'actual_rule_application': 'NOT_RUN'})
for e in entries:
    data = (HERE / e['file']).read_bytes()
    assert len(data) == e['bytes'] and sha(data) == e['sha256']
assert sorted(str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()) == sorted(payload + ['FINITE-ALLOWLIST.json', 'SHA256SUMS', 'SEAL.json'])
print(json.dumps({'payload_count': len(entries), 'sidecars': 3, 'self_readback': 'EXACT',
                  'hashes': {n: sha((HERE / n).read_bytes()) for n in
                             ['FINAL-REPORT.md', 'FINAL-REVIEW.json', 'FINITE-ALLOWLIST.json', 'SEAL.json']}}, sort_keys=True))
