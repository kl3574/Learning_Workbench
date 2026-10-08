"""Freeze the native publication supplement and preserve the original failed reader."""
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


final = json.loads((HERE / 'v2-REVIEW.json').read_bytes())
final.update({'preserved_original_helper_failure': 'REVIEW.json/05-AUDIT.stdout/05-AUDIT.stderr',
              'helper_failure_classification': 'Reviewer enum/count assumptions, not source/product defects',
              'auxiliary_preview_failure': '06-INITIAL-PREVIEW-TOOL-FAILURE.json',
              'final_actual_tool_chunk_id': '6e59c3', 'final_actual_exit_code': 0})
write('FINAL-REVIEW.json', final)
write('09-AUDIT-COMMANDS-AND-RECEIPTS.json', {'commands': [
    {'argv': ['/usr/bin/python3', 'audit_native_packet.py'], 'cwd': str(HERE), 'actual_tool_chunk_id': '0e8009',
     'actual_exit_code': 1, 'script': meta('audit_native_packet.py'), 'stdout': meta('05-AUDIT.stdout'), 'stderr': meta('05-AUDIT.stderr')},
    {'argv': ['/usr/bin/python3', 'audit_native_packet_v2.py'], 'cwd': str(HERE), 'actual_tool_chunk_id': '6e59c3',
     'actual_exit_code': 0, 'script': meta('audit_native_packet_v2.py'), 'stdout': meta('08-AUDIT-V2.stdout'), 'stderr': meta('08-AUDIT-V2.stderr')}],
    'original_streams_saved_before_assertions': True, 'HOME_CODEX_HOME_override': False,
    'tests_original_scripts_model_remote_host_probes': 'NOT_RUN'})
v1names = ['audit_native_packet.py','01-ALL-16-ORIGIN-PREFIX-BINDINGS.json','02-FOUR-FULL-MAP-AND-FIVE-MUTATION-READBACK.json',
           '03-TIMING-POSITIVE-METADATA-READBACK.json','04-MANUAL-SCOPE-AND-SOURCE-READBACK.json','REVIEW.json','05-AUDIT.stdout','05-AUDIT.stderr']
write('10-ALL-ORIGINAL-V1-CAPTURE-HASHES.json', {'files': [meta(name) for name in v1names], 'all_retained': True})
files = ['audit_native_packet.py','audit_native_packet_v2.py','freeze_native_review.py',
         'v2-01-ALL-16-ORIGIN-PREFIX-BINDINGS.json','v2-02-FOUR-FULL-MAP-AND-FIVE-MUTATION-READBACK.json',
         'v2-03-TIMING-POSITIVE-METADATA-READBACK.json','v2-04-MANUAL-SCOPE-AND-SOURCE-READBACK.json','v2-REVIEW.json',
         'FINAL-REVIEW.json','REPORT.md','REVIEW.json','05-AUDIT.stdout','05-AUDIT.stderr',
         '06-INITIAL-PREVIEW-TOOL-FAILURE.json','07-VALIDATOR-CORRECTION-RECEIPT.json',
         '08-AUDIT-V2.stdout','08-AUDIT-V2.stderr','09-AUDIT-COMMANDS-AND-RECEIPTS.json','10-ALL-ORIGINAL-V1-CAPTURE-HASHES.json']
write('FINITE-ALLOWLIST.json', {'finite_payload_count': len(files), 'entries': [meta(name) for name in files],
    'source_package_file_count': 18, 'originals_independently_bound': 16, 'manual_scoped_summary_count': 1,
    'scope': 'Finite thirteenth package supplement only; prior twelve-package seal unchanged',
    'excluded': ['actual private raw logs, images, databases, profiles, archives, payloads', 'all other cache data',
                 'other original159/23 command sets not independently reopened here']})
with (HERE / 'SHA256SUMS').open('x') as stream:
    for name in files + ['FINITE-ALLOWLIST.json']:
        stream.write(sha((HERE / name).read_bytes()) + '  ' + name + '\n')
write('SEAL.json', {'finite_payload_count': len(files), 'report': meta('REPORT.md'), 'final_review': meta('FINAL-REVIEW.json'),
    'manifest': meta('FINITE-ALLOWLIST.json'), 'sha256sums': meta('SHA256SUMS'), 'final_audit_exit': 0,
    'original_audit_failure_exit': 1, 'Standards_new_blocking': 0, 'Spec_new_blocking': 0,
    'M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_UNLOCKED'})
for name in set(files + v1names + ['FINITE-ALLOWLIST.json', 'SHA256SUMS', 'SEAL.json']):
    (HERE / name).chmod(0o444)
print(json.dumps({'finite_payload_count': len(files), 'report': meta('REPORT.md'), 'final_review': meta('FINAL-REVIEW.json'),
                  'allowlist': meta('FINITE-ALLOWLIST.json'), 'seal': meta('SEAL.json')}), flush=True)
