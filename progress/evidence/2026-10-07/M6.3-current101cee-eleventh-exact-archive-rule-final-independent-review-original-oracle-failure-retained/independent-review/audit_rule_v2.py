"""Correct the reviewer's line-terminator oracle; preserve every v1 artifact."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
def sha(data):
    return hashlib.sha256(data).hexdigest()
def put(name, value):
    with (HERE / name).open('xb') as stream:
        stream.write(value)
def put_json(name, value):
    put(name, (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())

old = json.loads((HERE / 'REVIEW.json').read_bytes())
plan = json.loads((HERE / 'safe-plan/RULE-PLAN.json').read_bytes())
excerpt = json.loads((HERE / '02-SAFE-LINE-AND-MANIFEST-BINDINGS.json').read_bytes())
line = excerpt['line_utf8_with_newline'].encode()
assert line == b'+[plugin builtin:vite-reporter] \n'
content = line[:-1]  # remove only the LF; retain the actual trailing blank
assert old['findings'] == ['line_sha']
assert len(old['checks']) == 19 and sum(old['checks'].values()) == 18
final = dict(old)
final['checks'] = dict(old['checks'])
final['checks']['line_sha'] = sha(content) == plan['line_sha256']
final['findings'] = [name for name, okay in final['checks'].items() if not okay]
final['Standards_new_blocking'] = final['Spec_new_blocking'] = len(final['findings'])
final['original_line_content_sha256_excluding_LF'] = sha(content)
final['original_line_plus_LF_sha256'] = sha(line)
final['line_terminator_oracle_correction'] = 'v1 included LF; plan binds content excluding LF, preserving trailing blank; no original/plan modification'
final['original_v1_receipt'] = {'actual_tool_chunk': 'ff714e', 'actual_exit': 1,
                               'stdout': '05-AUDIT.stdout', 'stderr': '05-AUDIT.stderr'}
final['v1_REPORT_status'] = 'Retained draft, not final admission: its opening 0-blocking assertion was premature; v1 REVIEW actually records one reviewer-oracle failure'
final['product_commands_repeated'] = False
put_json('FINAL-REVIEW.json', final)
put('FINAL-REPORT.md', ('''The final independent finite review has 0 new blocking issues on Standards and 0 on Spec. All 19 bounded checks pass. The proposed file preserves the entire earlier ten-rule prefix (SHA256 e9b42216d7c6171d3d0e8a13a064a477ce7eeb6e8cb5a0fb31e5169100518a20), then appends exactly one 157-byte literal progress path with -whitespace (proposed SHA256 1bc2eeba8343bd4b536e98ce2ba6a7b6e244fadbc4e46099ee5c7b7484723990). It matches no nonprogress path and contains no wildcard.

The archive's raw and published bytes are identical: 1783 bytes, SHA256 bd2597086e2eaaea5c1e5eb28fba28233c7c17b8b04ffd1e0c2012ed99aac228. Its raw finite allowlist and published packet manifest bind the exact source package/file. Literal HOME/runner prefix occurrences are zero. Original line 7 has one leading plus and a trailing blank. Its content SHA excluding LF is 967be8409ee904456c81504902812ccea74d3c83cc6069e98e12ebf2534b5069; the same line including LF is 7c6265363ad0ce7bb76e10d36e65f35ab45e35db201c6ff59e6cb8e2c834d21f. The recorded new default git diff --cached --check is actual exit 2; its 203-byte stdout reports only this path, and its two plus characters include the diff's own prefix.

All v1 review originals remain unchanged. V1 ff714e actually exited 1 because the reviewer incorrectly hashed line plus LF against a plan hash excluding LF. Its REVIEW records that one guard failure. Its REPORT's opening 0-blocking sentence was premature and is not final admission. This final review corrects only that reviewer oracle, preserves the trailing blank, and uses already captured bound metadata; it does not alter source, plan, archive, or old stdout and runs no product command. Root's initial helper 782298/exit1 also remains plan metadata; separately captured helper shell streams are NOT_CAPTURED. Root's corrected 630b53 is plan-only provenance, not a product PASS.

The rule disables Git whitespace checking for the entire one exact archive file, not only line 7. It does not change privacy scanners or source checks. No archived script import, tests, host probes, source/index/canonical/remote mutation or rule application was performed by this reviewer. Post-apply default diff checking is NOT_RUN here. Escaped JSON excerpts preserve the line without copying a new raw trailing-whitespace stdout artifact. No platform acceptance or original fixed-101 gate relabeling is claimed. FINAL-REPORT.md and FINAL-REVIEW.json are the final admission files; prior REPORT.md and REVIEW.json remain v1 diagnostics.
''').encode())
print(json.dumps({'Standards_new_blocking': final['Standards_new_blocking'],
                  'Spec_new_blocking': final['Spec_new_blocking'],
                  'checks_passed': sum(final['checks'].values()),
                  'prior_ff714e_exit1': 'RETAINED', 'source_plan_modified': False,
                  'tests_rerun': False}, sort_keys=True))
assert not final['findings'], final['findings']
