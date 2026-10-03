"""Exact four read-only projection functions from the frozen a944 verifier; C is this package."""
from pathlib import Path
import json
import hashlib
C = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text())

def meta(b):
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def selected(record, keys):
    return {k: record[k] for k in keys if k in record}

def diagnostic(path):
    d = read(path)
    frozen, m = d['frozen_observation'], d['mechanism']
    network = frozen['events']
    requests = [r for r in network if r['kind'] == 'request' and
                '/tutor/runs/' in r.get('path', '')]
    # Existing diagnostic uses /runs/... rather than /tutor/runs/... .
    if not requests:
        requests = [r for r in network if r['kind'] == 'request' and
                    '/runs/' in r.get('path', '')]
    projected = []
    for r in requests:
        projection = selected(r, ['id', 'elapsed_ms', 'method', 'after_seq'])
        projection['endpoint'] = 'events' if '/events' in r['path'] else 'run'
        if '?after_seq=' in r['path']:
            projection['after_seq'] = int(r['path'].split('?after_seq=')[1])
        projection['lifecycle'] = [selected(e, ['elapsed_ms', 'kind', 'status', 'failure'])
                                   for e in network if e.get('id') == r['id'] and e['kind'] != 'request']
        projected.append(projection)
    api_wrapper = m['post_assertion_api']
    api = api_wrapper.get('value', {})
    api_records = api.get('records', [])
    safe_api = []
    for r in api_records:
        q = selected(r, ['ordinal', 'source_ns', 'stage', 'after', 'seq', 'revision', 'status', 'http_status', 'event'])
        if 'correlation' in r:
            q['span_ordinal'] = int(r['correlation'].rsplit(':', 1)[1])
        safe_api.append(q)
    browser = []
    for r in m['frozen_browser_records']:
        q = selected(r, ['ordinal', 'operation', 'after', 'seq', 'revision', 'status', 'stage', 'source_ms', 'delivered_ms'])
        if 'span' in r:
            q['span_ordinal'] = int(r['span'].rsplit(':', 1)[1])
        browser.append(q)
    return {
        'source': str(path.relative_to(C)), **meta(path.read_bytes()),
        'projection_scope': 'Explicit selected metadata, not a complete log; exact original retained.',
        'assertion': d['assertion'],
        'node': {'clock': 'Node observer performance.now elapsed_ms; frozen at assertion',
                 'events': len(network), 'omitted': frozen['omitted_events'],
                 'last_dom_delivered': frozen['last_dom_delivered'], 'run_requests': projected},
        'browser': {'clock': 'separate browser epoch source_ms; delivered_ms is Node arrival',
                    'records': browser, 'invalid': m['invalid_deliveries'], 'omitted': m['omitted_deliveries'],
                    'dom_projections_count': len(m['frozen_dom_projections']),
                    'dom_matched_count': sum(r['matched_source'] for r in m['frozen_dom_projections'])},
        'api': {'clock': 'separate API perf_counter_ns, periodic snapshot read after assertion; no Node deadline placement',
                'read_state': api_wrapper['state'],
                **selected(api, ['snapshot_source_ns', 'omitted', 'invalid', 'snapshot_contended']),
                'records': safe_api},
        'post_assertion': {**selected(d['post_assertion'], ['phase', 'started_ms', 'finished_ms', 'wait_limit_ms']),
                           'run_diagnostic_operation_state': d['post_assertion']['run']['state'],
                           'runtime': d['post_assertion']['runtime']},
    }
