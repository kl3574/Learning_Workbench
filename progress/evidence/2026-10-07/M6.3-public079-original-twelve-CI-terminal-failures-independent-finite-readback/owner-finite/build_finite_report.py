"""Render only the already reviewed finite original-terminal readback."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = HERE / 'FINAL-READBACK.json'
    record = json.loads(source.read_text())
    assert record['readback_job_count'] == 12
    assert all(event['status'] == 'completed' for event in record['events'])
    assert all(job['status'] == 'completed' and job['independent_read'] != 'NOT_RUN' for job in record['jobs'])
    lines = [
        '# Original079 attempt1 — independent terminal CI readback', '',
        'Both original events and all12 original jobs were read from the sole root collector. This report does not replace any original failure with a later local fix or rerun. M6.3 remains **NOT_ACCEPTED**.', '',
        'Source public head: `079a008cf88b37e4517cb391503a1e7393ccf374`. Original push checkout is that SHA; original PR checkout is `e9eb82d41dd87649be6c8090c35b5052ccb1319c`, independently found in each original job log. The existing root current079 Git readback records whole tree `eea569fec4f6b3fd209ed96eb29e6d052f0e9b1e`,23175 identical entries. This audit reads and hashes that current receipt; it does not perform a fresh Git comparison/fetch and does not borrow the older1e24ff tree.', '',
        '**CI working tree before: NOT_CAPTURED. CI working tree after: NOT_CAPTURED.** Git object equality does not supply those missing execution-time facts.', '',
        'Counts are presented separately for each original job within its event. Repeated suites/events are never added into a distinct-test or platform acceptance total.', '',
    ]
    safe = []
    for event in sorted(record['events'], key=lambda event: event['event'], reverse=True):
        jobs = [job for job in record['jobs'] if job['run_id'] == event['id']]
        success = sum(job['conclusion'] == 'success' for job in jobs)
        failure = sum(job['conclusion'] == 'failure' for job in jobs)
        lines.extend([f"## {event['event']} run{event['id']} / attempt1", '',
                      f"Original API event terminal: `{event['status']}/{event['conclusion']}`. Within this event only: {success} successful jobs, {failure} failed jobs; other conclusions: {len(jobs)-success-failure}.", '',
                      '| Job / original ID | API conclusion | Original footer / static result | Original bytes / SHA256 |',
                      '|---|---|---|---|'])
        for job in sorted(jobs, key=lambda job: job['name']):
            footer = [item['text'].strip('= ') for item in job['safe_excerpt'] if item['category'] == 'original_footer']
            if job['name'] == 'security-publication':
                footer += [item['text'] for item in job['safe_excerpt'] if item['text'].startswith('PASS: scanned')]
            if not footer:
                footer = ['No completed test summary captured; no test-count inference']
            summary = '; '.join(footer).replace('|', '\\|')
            lines.append(f"| {job['name']} / {job['id']} | {job['conclusion']} | {summary} | {job['original_bytes']} / `{job['original_sha256']}` |")
            safe.extend([f"{job['event']} run{job['run_id']} attempt1 job{job['id']} {job['name']}",
                         f"original {job['original_file']} bytes={job['original_bytes']} sha256={job['original_sha256']}"])
            safe.extend(f"L{item['line']} [{item['category']}] {item['text']}" for item in job['safe_excerpt'])
            safe.append('')
        lines.append('')
    lines.extend([
        '## Preserved failures, ENV, and cause boundaries', '',
        '- Original push integration112830648805: the only FAILED footer names `test_forward_guards_preserve_existing_source_rows_rowids_and_original_http_acks`; the assertion is503==202 at shared `tests/integration/test_codex_turn_consent_http.py:91`. This proves the original full gate failed; it does not reveal the503 cause. Cause: **UNRESOLVED**. No later90c8 patch or bounded subset is used to revise this result.',
        '- Original PR integration112830674741: independently captured63380B, SHA256 `e1e9a4eac717ab53dd0d8ee6da6f232d53b04209534d6ce1274415f08b552d0e`;2521 collected;1 FAIL,2518 PASS,2 ENV skips,2 warnings in4497.52s. Its only FAILED footer names the same forwardguards test,503==202 at the same shared fixture:91; original step exit1. Cause: **UNRESOLVED**. Its count remains separate from push integration.',
        '- Original PR browser112830674946: the only failed test is `review.spec.ts:36:1`, with the reader query URL poll at147:75 and original `Test timeout of 30000ms exceeded`. The30000ms belongs to the whole test; this report does not infer a poll-specific timeout, flake classification, or underlying API/navigation cause. Cause: **UNRESOLVED**.',
        '- Integration footer ENV skips are retained as original CI skips, not counted as PASS: authoring actual sealed numeric runtime did not execute the calculator; actual sealed Restore evaluator did not return a numeric PASS. The markers explicitly retain original failure/no-fallback boundaries. Their runtime cause is not independently established by this audit.', '',
        'All final integration failed-test identifiers, ENV reason lines, original count footers and step exit lines are retained in FINAL-READBACK.json and SAFE_EXCERPTS.txt. If a final job lacks a completed test summary, its API terminal is reported without inferring unobserved test counts.', '',
        '## Provenance and finite publication candidate', '',
        f"Final producer snapshot: `{record['source_snapshot']}` at `{record['snapshot_observed_utc']}`; SHA256 `{record['snapshot_sha256']}`. Final independent readback SHA256 `{digest(source)}`.", '',
        'For each of12 jobs, the independent local reader consumed the complete original stdout bytes, checked exact byte length/SHA256 and empty stderr against the original collector receipt, checked attempt/event/job identity and exact retrieval command, and extracted only explicit approved line classes. Log retrieval exit0 is kept distinct from original test-step exit and job conclusion. Full raw logs remain in the private original collector directory.', '',
        'Public candidate allowlist: explicit original command/version/footer lines with physical line numbers; reviewed safe failed assertion/test locations and named ENV reasons; byte/hash metadata and projected event/job identity. Excluded: AUTH Case repr, fixture bodies, raw API payloads, unselected raw log lines, ZIP/DB/PNG/profile content, older CI results and later fix/patch results. SAFE_EXCERPTS.txt strips only timestamp/ANSI decoration; its line references point to original physical log lines. Bare future failure IDs omit any unreviewed suffix.', '',
        'The original early8 seal and the separate11-job stage remain unchanged. This independent reader does not fetch, start a watcher, retry/dispatch/cancel CI, operate a model/CLI, run a product test/probe or modify any checkout. NOT_RUN: new local/full CI/product acceptance or production model execution. Independent host/runtime qualification: NOT_CAPTURED. Whole M6.3: NOT_ACCEPTED.', '',
        'Root may review the finite candidate before copying it into progress evidence. The private root captures are not in the publication allowlist.', '',
    ])
    for name, content in (('REPORT.md', '\n'.join(lines)), ('SAFE_EXCERPTS.txt', '\n'.join(safe))):
        path = HERE / name
        assert not path.exists()
        path.write_text(content + '\n')
    files = ['FINAL-READBACK.json', 'REPORT.md', 'SAFE_EXCERPTS.txt', 'audit_terminal_final.py',
             'build_finite_report.py', 'final-local.log', 'FINAL-LOCAL-COMMAND-RECEIPT.json']
    allowlist = {'version': 'public079-original-terminal-finite-candidate-v1',
                 'status': 'ROOT_REVIEW_REQUIRED_FINITE_CANDIDATE_NOT_PLATFORM_ACCEPTANCE',
                 'files': [{'path': name, 'bytes': (HERE/name).stat().st_size, 'sha256': digest(HERE/name)} for name in files],
                 'included_seal_sidecars': ['CANDIDATE-ALLOWLIST.json', 'FINAL-SHA256SUMS'],
                 'private_raw_logs_publishable': False, 'whole_M6_3': 'NOT_ACCEPTED'}
    destination = HERE / 'CANDIDATE-ALLOWLIST.json'
    assert not destination.exists()
    destination.write_text(json.dumps(allowlist, indent=2) + '\n')
    print(json.dumps({'report_sha256': digest(HERE/'REPORT.md'), 'allowlist_sha256': digest(destination),
                      'report': str(HERE/'REPORT.md'), 'jobs': 12}, sort_keys=True))


if __name__ == '__main__':
    main()
