"""Read-only review of one explicitly named archival whitespace rule."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = Path('$HOME/.cache/learning-workbench-acceptance')
PLAN = ROOT / 'm63-current101-eleventh-exact-archive-rule-plan-oct07'
CHECKS = ROOT / 'm63-current101-final-stage-and-publication-checks-oct07'
PRIOR = ROOT / 'm63-current101-exact-archive-whitespace-independent-oct07'
CANON = ROOT / 'm62-public-safe-oct02'

def sha(data):
    return hashlib.sha256(data).hexdigest()
def put(name, data):
    p = HERE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as stream:
        stream.write(data)
def put_json(name, value):
    put(name, (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())

read_bindings = []
def read(p):
    data = p.read_bytes()
    read_bindings.append({'path': str(p), 'bytes': len(data), 'sha256': sha(data)})
    return data

plan_raw = read(PLAN / 'RULE-PLAN.json')
plan = json.loads(plan_raw)
before = read(PLAN / 'before.gitattributes')
proposed = read(PLAN / 'proposed.gitattributes')
prior_proposed = read(PRIOR / '03-proposed.gitattributes')
command_raw = read(CHECKS / '09-original-default-staged-diff-command.json')
receipt_raw = read(CHECKS / '09-original-default-staged-diff-receipt.json')
command = json.loads(command_raw)
receipt = json.loads(receipt_raw)
diff_stdout = read(CHECKS / '09-original-default-staged-diff.stdout')
diff_stderr = read(CHECKS / '09-original-default-staged-diff.stderr')
path = plan['path']
source_path = ROOT / plan['source_package'] / plan['source_relative']
raw = read(source_path)
published = read(CANON / path)
packet_dir = (CANON / path).parents[1]
manifest_raw = read(packet_dir / 'manifest.json')
manifest = json.loads(manifest_raw)
entry = next(e for e in manifest['entries']
             if e['file'] == str((CANON / path).relative_to(packet_dir)))
raw_manifest = json.loads(read(PRIOR / 'FINITE-ALLOWLIST.json'))
raw_entry = next(e for e in raw_manifest['entries'] if e['file'] == plan['source_relative'])
original_line = raw.splitlines(keepends=True)[plan['original_line'] - 1]
expected_line = b'+[plugin builtin:vite-reporter] \n'
new_rule = path.encode() + b' -whitespace\n'
normalised = raw.replace(b'$HOME', b'$HOME').replace(b'$RUNNER_HOME', b'$RUNNER_HOME')
checks = {
    'before_exact_previous_reviewed_proposal': before == prior_proposed,
    'before_hash': sha(before) == plan['before_sha256'] == 'e9b42216d7c6171d3d0e8a13a064a477ce7eeb6e8cb5a0fb31e5169100518a20',
    'proposed_hash': sha(proposed) == plan['proposed_sha256'] == '1bc2eeba8343bd4b536e98ce2ba6a7b6e244fadbc4e46099ee5c7b7484723990',
    'prefix_exact_single_append': before.endswith(b'\n') and proposed == before + new_rule,
    'single_literal_progress_file': path.startswith('progress/evidence/2026-10-07/') and
        not any(c in path for c in '*?[]\\\t\r\n ') and '..' not in Path(path).parts,
    'new_path_not_previously_matched_literally': new_rule not in before.splitlines(keepends=True),
    'source_manifest_binding': entry['source_package'] == plan['source_package'] and
        entry['source_relative'] == plan['source_relative'],
    'raw_sha_binding': sha(raw) == plan['raw_sha256'] == entry['raw_sha256'] == raw_entry['sha256'],
    'published_sha_binding': sha(published) == plan['published_sha256'] == entry['published_sha256'],
    'raw_published_byte_binding': len(raw) == len(published) == plan['published_bytes'] == raw_entry['bytes'] == 1783,
    'only_literal_prefix_normalisation': published == normalised and entry['transformation'] == 'none' and raw == published,
    'line7_single_plus_trailing_blank': plan['original_line'] == 7 and original_line == expected_line,
    'line_sha': sha(original_line) == plan['line_sha256'],
    'original_command': command['argv'] == ['git', 'diff', '--cached', '--check'],
    'original_default_exit2': receipt['actual_exit'] == plan['default_diff_original_exit'] == 2,
    'original_stream_receipt_bindings': len(diff_stdout) == receipt['stdout_bytes'] and
        sha(diff_stdout) == receipt['stdout_sha256'] and len(diff_stderr) == receipt['stderr_bytes'] and
        sha(diff_stderr) == receipt['stderr_sha256'],
    'only_one_reported_path': diff_stdout.splitlines(keepends=True) ==
        [path.encode() + b':7: trailing whitespace.\n', b'+' + original_line],
    'old_helper_failure_retained_metadata': plan['helper_failure_retained']['tool_chunk'] == '782298' and
        plan['helper_failure_retained']['actual_exit'] == 1,
    'plan_no_apply_or_test_rerun': plan['apply'] == 'NOT_YET' and plan['tests_rerun'] is False
}
findings = [name for name, result in checks.items() if not result]
put_json('01-EXACT-READ-BINDINGS.json', {'entries': read_bindings, 'count': len(read_bindings)})
put_json('02-SAFE-LINE-AND-MANIFEST-BINDINGS.json', {
    'raw_manifest_entry': raw_entry, 'published_manifest_entry': entry,
    'raw_bytes': len(raw), 'published_bytes': len(published),
    'raw_sha256': sha(raw), 'published_sha256': sha(published),
    'HOME_prefix_occurrences': raw.count(b'$HOME'),
    'RUNNER_prefix_occurrences': raw.count(b'$RUNNER_HOME'),
    'original_line_number': 7, 'line_utf8_with_newline': original_line.decode(),
    'line_sha256': sha(original_line),
    'default_diff_stdout_utf8': diff_stdout.decode(),
    'raw_stdout_copy': False, 'representation': 'JSON escaped line only; no trailing-whitespace artifact copied'
})
put('safe-plan/RULE-PLAN.json', plan_raw)
put('safe-plan/before.gitattributes', before)
put('safe-plan/proposed.gitattributes', proposed)
put('03-ORIGINAL-DIFF-COMMAND.json', command_raw)
put('04-ORIGINAL-DIFF-RECEIPT.json', receipt_raw)
review = {
    'Standards_new_blocking': len(findings), 'Spec_new_blocking': len(findings),
    'findings': findings, 'checks': checks, 'appended_rule_count': 1,
    'appended_bytes': len(new_rule), 'literal_progress_path': path,
    'source_or_index_or_canonical_or_remote_mutation': False,
    'tests_or_archived_script_import_or_host_probe': False,
    'actual_application': 'NOT_RUN_BY_REVIEWER',
    'post_apply_default_diff_check': 'NOT_RUN',
    'initial_helper_failure': 'Metadata retained; exact separate shell streams NOT_CAPTURED; corrected root helper 630b53 is a plan-only provenance statement',
    'whitespace_scope': 'whole exact archive file; not limited to line7; no wildcard/nonprogress match',
    'whole_platform_acceptance': 'NOT_CLAIMED'
}
put_json('REVIEW.json', review)
put('REPORT.md', ('''The independent finite plan review found 0 new blocking issues on Standards and 0 on Spec. Before bytes are identical to the earlier reviewed ten-rule proposal (SHA256 e9b42216d7c6171d3d0e8a13a064a477ce7eeb6e8cb5a0fb31e5169100518a20). The new proposal preserves that entire prefix and appends exactly one 157-byte literal progress path with -whitespace (SHA256 1bc2eeba8343bd4b536e98ce2ba6a7b6e244fadbc4e46099ee5c7b7484723990).

The bound archive is 1783 bytes with raw and published SHA256 bd2597086e2eaaea5c1e5eb28fba28233c7c17b8b04ffd1e0c2012ed99aac228. Both its original finite allowlist and published packet manifest bind it to the named source package/file. Literal HOME and runner prefix occurrence counts are zero, and transformation is none. Original line 7 contains one leading plus and the preserved Vite trailing blank. The newer diff output adds its own diff plus, explaining its two plus characters. Its original git diff --cached --check receipt is actual exit 2, stdout 203 bytes and empty stderr, with exactly the one reported path.

The initial root helper failure 782298/exit1 remains recorded in RULE-PLAN.json; its separately captured shell streams are NOT_CAPTURED. The corrected 630b53 plan-only helper is not relabeled as a product pass. No archived script was imported or executed. No tests, host probes, source/index/canonical/remote mutations or application were performed by this reviewer. The rule disables Git whitespace checking for the entire single exact archived file, not only line 7; it does not disable privacy scanning or source checks, and makes no platform acceptance claim. Post-application default diff checking is NOT_RUN here. Safe excerpts use escaped JSON, so this review adds no raw trailing-whitespace stdout artifact.
''').encode())
print(json.dumps({'checks': len(checks), 'findings': findings,
                  'Standards_new_blocking': len(findings), 'Spec_new_blocking': len(findings),
                  'read_bindings': len(read_bindings), 'appended_bytes': len(new_rule),
                  'raw_stdout_copy': False, 'apply': 'NOT_RUN'}, sort_keys=True))
assert not findings, findings
