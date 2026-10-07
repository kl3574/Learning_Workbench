"""Read-only exact archival attribute proposal audit; never apply or execute product checks."""
from pathlib import Path
import hashlib
import json
import re
import time

HERE = Path(__file__).parent
BASE = Path('$HOME/.cache/learning-workbench-acceptance')
PLAN = BASE / 'm63-current101-exact-archive-whitespace-plan-oct07'
DIFF = BASE / 'm63-current101-progress-commit-preconditions-oct07/diff-check'
REPO = BASE / 'm62-public-safe-oct02'
FIXED = BASE / 'm63-integrated-1564-static-source-oct07'
HEAD = '101cee47d8e746dddac81fb6e8829069fcabff09'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def preserve(name, source):
    data = source.read_bytes()
    with (HERE / name).open('xb') as stream:
        stream.write(data)
    return data


started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
plan_data = preserve('01-RULE-PLAN.json', PLAN / 'RULE-PLAN.json')
before = preserve('02-before.gitattributes', PLAN / 'before.gitattributes')
proposed = preserve('03-proposed.gitattributes', PLAN / 'proposed.gitattributes')
command_data = preserve('04-original-diff-command.json', DIFF / 'command.json')
stdout = preserve('05-original-diff-stdout', DIFF / 'stdout')
stderr = preserve('06-original-diff-stderr', DIFF / 'stderr')
receipt_data = preserve('07-original-diff-receipt.json', DIFF / 'receipt.json')
plan = json.loads(plan_data)
command, receipt = json.loads(command_data), json.loads(receipt_data)
owner_map = json.loads((BASE / 'm63-integrated-1564-static-evidence-oct07/03-SOURCE-BEFORE-SETUP.json').read_text())
source_paths = {row['path'] for row in owner_map['rows']}
admission = json.loads((BASE / 'm63-current101-progress-finite-publication-review-oct07/10-ALL-370-ENTRY-ORIGIN-PREFIX-BINDINGS.json').read_text())
admitted = {row['package'] + row['file']: row for row in admission['entries']}
diagnostics = [{'path': path, 'line': int(line), 'reason': reason.rstrip('.')}
               for path, line, reason in re.findall(r'^(.*?):(\d+): (new blank line at EOF\.|trailing whitespace\.)$', stdout.decode(), re.M)]
extra = proposed[len(before):] if proposed.startswith(before) else b''
rules = [line for line in extra.decode().splitlines() if line and not line.startswith('#')]
facts, findings = [], []
for binding in plan['bindings']:
    path = binding['path']
    published = (REPO / path).read_bytes()
    raw_path = BASE / binding['raw_source_package'] / binding['raw_source_relative']
    raw = raw_path.read_bytes()
    pub_line = published.splitlines(keepends=True)[binding['line'] - 1]
    raw_line = raw.splitlines(keepends=True)[binding['line'] - 1]
    origin = admitted.get(path)
    diagnostic = {'path': path, 'line': binding['line'], 'reason': binding['original_whitespace']}
    checks = {
        'exact_progress_path': path.startswith('progress/evidence/2026-10-07/'),
        'literal_no_wildcard_or_special_pattern': not any(char in path for char in '*?[]!\\\t\n '),
        'not_a_nonprogress_input': path not in source_paths,
        'only_unset_whitespace_attribute': binding['rule'] == path + ' -whitespace',
        'rule_in_append': binding['rule'] in rules,
        'original_default_diagnostic_bound': diagnostic in diagnostics,
        'admitted_publication_origin_bound': bool(origin) and origin.get('source_package') == binding['raw_source_package'] and
            origin.get('source_relative') == binding['raw_source_relative'],
        'raw_sha_exact': sha(raw) == binding['raw_sha256'],
        'published_sha_exact': sha(published) == binding['published_sha256'],
        'published_is_exact_allowed_prefix_copy': raw.replace(b'$HOME', b'$HOME').replace(b'$RUNNER_HOME', b'$RUNNER_HOME') == published,
        'raw_line_sha_exact': sha(raw_line) == binding['original_line_sha256'],
        'published_line_sha_exact': sha(pub_line) == binding['original_line_sha256'],
        'line_bytes_unchanged': raw_line == pub_line,
    }
    if binding['original_whitespace'] == 'new blank line at EOF':
        checks['actual_blank_line_at_eof'] = pub_line == b'\n' and binding['line'] == len(published.splitlines(keepends=True))
    else:
        checks['actual_original_vite_trailing_space'] = pub_line == b'[plugin builtin:vite-reporter] \n'
    facts.append({'path': path, 'line': binding['line'], 'reason': binding['original_whitespace'],
                  'raw_bytes': len(raw), 'raw_sha256': sha(raw), 'published_bytes': len(published),
                  'published_sha256': sha(published), 'raw_line_bytes': len(raw_line), 'raw_line_sha256': sha(raw_line),
                  'published_line_sha256': sha(pub_line), 'source_package': binding['raw_source_package'],
                  'source_relative': binding['raw_source_relative'], 'rule': binding['rule'], 'checks': checks})
    if not all(checks.values()):
        findings.append({'path': path, 'failed_checks': [name for name, passed in checks.items() if not passed]})
before_fixed = (FIXED / '.gitattributes').read_bytes()
global_checks = {
    'plan_anchor_fixed101': plan['source_anchor'] == HEAD and owner_map['head'] == HEAD,
    'plan_not_applied_status': plan['status'] == 'PRIVATE_EXACT_RULE_PLAN_NOT_APPLIED',
    'before_expected_sha': sha(before) == plan['before_sha256'] == '7ad12b1033abce056aa1c9890dd5ad32f5c9723b35e8012a3d64c8fdfbebfdc1',
    'proposed_expected_sha': sha(proposed) == plan['proposed_sha256'] == 'e9b42216d7c6171d3d0e8a13a064a477ce7eeb6e8cb5a0fb31e5169100518a20',
    'before_exact_fixed_source_bytes': before == before_fixed,
    'existing_attribute_bytes_untouched_prefix': proposed.startswith(before),
    'exactly_10_unique_appended_rules': len(rules) == len(set(rules)) == len(plan['bindings']) == 10,
    'only_declared_10_rules_appended': set(rules) == {binding['rule'] for binding in plan['bindings']},
    'original_command_exact': command['argv'] == ['git', 'diff', '--cached', '--check'],
    'original_diff_failure_preserved': receipt['actual_exit'] == plan['default_diff_actual_exit'] == 2,
    'original_stdout_binding': len(stdout) == receipt['stdout_bytes'] and sha(stdout) == receipt['stdout_sha256'],
    'original_stderr_binding': len(stderr) == receipt['stderr_bytes'] == 0 and sha(stderr) == receipt['stderr_sha256'],
    'all_10_original_diagnostics_covered': len(diagnostics) == 10 and len({d['path'] for d in diagnostics}) == 10,
    'nine_eof_one_vite': sum(d['reason'] == 'new blank line at EOF' for d in diagnostics) == 9 and
        sum(d['reason'] == 'trailing whitespace' for d in diagnostics) == 1,
    '1563_other_source_paths_unmatched': len(source_paths - {'.gitattributes'}) == 1563 and not ({b['path'] for b in plan['bindings']} & source_paths),
}
for name, passed in global_checks.items():
    if not passed:
        findings.append({'global_check': name})
result = {
    'started_utc': started, 'ended_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'source_anchor': HEAD, 'plan_source_sha256': sha(plan_data),
    'before_sha256': sha(before), 'proposed_sha256': sha(proposed), 'before_bytes': len(before), 'proposed_bytes': len(proposed),
    'global_checks': global_checks, 'rules': facts, 'findings': findings,
    'Standards_new_blocking': len(findings), 'Spec_new_blocking': len(findings),
    'actual_original_diff_exit': 2, 'original_diagnostic_count': 10,
    'actual_plan_application': 'NOT_RUN', 'proposed_after_application_diff_result': 'NOT_RUN; not fabricated as PASS',
    'effect_scope': '10 exact archived progress paths only; whitespace attribute alone; 1563 other nonprogress path names cannot match. Existing attributes unchanged.',
    'secret_scanner_or_business_checks': 'UNCHANGED_BY_PLAN; no scanner/check was executed in this read-only review',
    'actual_canonical_before_after': 'NOT_CAPTURED_BY_THIS_OWNER; private before compared with fixed101 isolated Git source bytes only',
    'publication_files_rewritten_or_trimmed': False, 'HOME_CODEX_HOME_override': False,
    'runtime_model_tests_browser_remote_host_probes': 'NOT_RUN', 'canonical_mutation': False,
    'root_apply_order': plan['apply_order'], 'M6_3': 'NOT_ACCEPTED', 'M7': 'NOT_UNLOCKED',
}
write('REVIEW.json', result)
print(json.dumps({'finding_count': len(findings), 'global_checks': global_checks,
                  'before_sha256': sha(before), 'proposed_sha256': sha(proposed), 'diagnostics': diagnostics}), flush=True)
assert not findings, 'All original audit facts retained before failing assertion'
