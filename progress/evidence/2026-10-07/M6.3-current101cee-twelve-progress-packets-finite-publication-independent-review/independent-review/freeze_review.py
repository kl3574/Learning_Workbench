"""Freeze the completed finite publication review, preserving actual audit captures."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def meta(name):
    data = (HERE / name).read_bytes()
    return {'file': name, 'bytes': len(data), 'sha256': sha(data)}


write('15-AUDIT-COMMAND.json', {
    'argv': ['/usr/bin/python3', 'audit_finite.py'], 'cwd': str(HERE),
    'actual_tool_chunk_id': '494a82', 'actual_tool_exit_code': 0,
    'script_sha256': sha((HERE / 'audit_finite.py').read_bytes()),
    'native_stdout': '14-AUDIT.stdout', 'native_stderr': '14-AUDIT.stderr',
    'execution': 'Original once read-only audit; no product/test/model/browser/remote execution',
    'HOME_CODEX_HOME_overrides': 'NONE; script does not read/set inherited host environment',
})
write('16-AUDIT-RECEIPT.json', {
    'actual_tool_chunk_id': '494a82', 'actual_exit_code': 0,
    'stdout': meta('14-AUDIT.stdout'), 'stderr': meta('14-AUDIT.stderr'),
    'streams_preserved_before_result_assertions': True,
    'original_result': meta('13-ACTUAL-AUDIT-RESULT.json'),
})
finite = [
    '00-READONLY-ENVIRONMENT.json', '03-ACTUAL-UNTRACKED-PACKAGE-LIST.json',
    '04-PACKAGE-IMMEDIATE-INVENTORY.json', '05-MANIFESTS-AND-REPORTS-READBACK.json',
    '06-INITIAL-METADATA-HELPER-TOOL-FAILURE.json', '08-EXPANDED-12-PACKAGE-MANIFESTS-READBACK.json',
    '09-PUBLISHER-RULE-READBACK.json', '10-ALL-370-ENTRY-ORIGIN-PREFIX-BINDINGS.json',
    '11-ALL-382-FINITE-FILE-INVENTORY.json', '12-MANUAL-SUMMARY-SCOPE-READBACK.json',
    '13-ACTUAL-AUDIT-RESULT.json', '14-AUDIT.stdout', '14-AUDIT.stderr',
    '15-AUDIT-COMMAND.json', '16-AUDIT-RECEIPT.json', 'audit_finite.py', 'freeze_review.py',
    'MANUAL-SCOPE-REVIEW.json', 'REPORT.md',
]
for group in ('01-canonical-status', '02-canonical-head', '07-canonical-status-after-named-static-package'):
    finite.extend(group + '/' + name for name in ('command.json', 'stdout', 'stderr', 'receipt.json'))
write('FINITE-ALLOWLIST.json', {
    'payload_count': len(finite), 'entries': [meta(name) for name in finite],
    'publication_packages': 12, 'publication_finite_files': 382, 'owner_origins': 358,
    'manual_scoped_summaries': 12,
    'scope': 'Read-only finite origin/scope review; not source/platform/runtime acceptance',
    'exclusions': ['active CURRENT/state contents', 'private source/runtime/API/auth/DB/ZIP/profile bodies',
                   'owned temp directory', 'all other cache data', 'pending attributes plan'],
})
with (HERE / 'SHA256SUMS').open('x') as stream:
    for name in finite + ['FINITE-ALLOWLIST.json']:
        stream.write(sha((HERE / name).read_bytes()) + '  ' + name + '\n')
write('SEAL.json', {
    'finite_payload_count': len(finite), 'report': meta('REPORT.md'),
    'manual_scope': meta('MANUAL-SCOPE-REVIEW.json'), 'manifest': meta('FINITE-ALLOWLIST.json'),
    'sha256sums': meta('SHA256SUMS'), 'actual_audit_exit': 0,
    'Standards_new_blocking': 0, 'Spec_new_blocking': 0,
    'M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_UNLOCKED',
})
for name in finite + ['FINITE-ALLOWLIST.json', 'SHA256SUMS', 'SEAL.json']:
    (HERE / name).chmod(0o444)
print(json.dumps({'finite_payload_count': len(finite), 'report': meta('REPORT.md'),
                  'manual_scope': meta('MANUAL-SCOPE-REVIEW.json'), 'manifest': meta('FINITE-ALLOWLIST.json'),
                  'seal': meta('SEAL.json')}), flush=True)
