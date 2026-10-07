"""Freeze actual read-only archival plan audit and its preserved default failure."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def meta(name):
    data = (HERE / name).read_bytes()
    return {'file': name, 'bytes': len(data), 'sha256': sha(data)}


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


write('09-AUDIT-COMMAND.json', {
    'argv': ['/usr/bin/python3', 'audit_plan.py'], 'cwd': str(HERE),
    'actual_tool_chunk_id': 'c4e8ac', 'script': meta('audit_plan.py'),
    'HOME_CODEX_HOME_overrides': 'NONE; script reads no host environment and spawns no child commands',
    'plan_application_tests_scanner_remote': 'NOT_RUN',
})
write('10-AUDIT-RECEIPT.json', {
    'actual_exit_code': 0, 'actual_tool_chunk_id': 'c4e8ac',
    'stdout': meta('08-AUDIT.stdout'), 'stderr': meta('08-AUDIT.stderr'),
    'streams_preserved_before_status_assertions': True,
    'original_default_diff_exit': 2, 'plan_application': 'NOT_RUN',
})
files = ['audit_plan.py', 'freeze_plan.py', '01-RULE-PLAN.json', '02-before.gitattributes', '03-proposed.gitattributes',
         '04-original-diff-command.json', '05-original-diff-stdout', '06-original-diff-stderr',
         '07-original-diff-receipt.json', '08-AUDIT.stdout', '08-AUDIT.stderr',
         '09-AUDIT-COMMAND.json', '10-AUDIT-RECEIPT.json', 'REVIEW.json', 'REPORT.md']
write('FINITE-ALLOWLIST.json', {'finite_payload_count': len(files), 'entries': [meta(name) for name in files],
                              'scope': 'Read-only exact 10 archival rules plan, before/proposed snapshots and original diff failure',
                              'source_anchor': '101cee47d8e746dddac81fb6e8829069fcabff09',
                              'original_diff_exit': 2, 'applied': False, 'M6_3': 'NOT_ACCEPTED'})
with (HERE / 'SHA256SUMS').open('x') as stream:
    for name in files + ['FINITE-ALLOWLIST.json']:
        stream.write(sha((HERE / name).read_bytes()) + '  ' + name + '\n')
write('SEAL.json', {'finite_payload_count': len(files), 'report': meta('REPORT.md'), 'review': meta('REVIEW.json'),
                    'manifest': meta('FINITE-ALLOWLIST.json'), 'sha256sums': meta('SHA256SUMS'),
                    'Standards_new_blocking': 0, 'Spec_new_blocking': 0, 'actual_audit_exit': 0,
                    'original_default_diff_exit': 2, 'plan_application': 'NOT_RUN', 'M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_UNLOCKED'})
for name in files + ['FINITE-ALLOWLIST.json', 'SHA256SUMS', 'SEAL.json']:
    (HERE / name).chmod(0o444)
print(json.dumps({'finite_payload_count': len(files), 'report': meta('REPORT.md'), 'review': meta('REVIEW.json'),
                  'allowlist': meta('FINITE-ALLOWLIST.json'), 'seal': meta('SEAL.json')}), flush=True)
