from pathlib import Path
import hashlib, json, subprocess

OUT = Path(__file__).resolve().parent
SEAL = OUT.parent / 'm63-broker-control-owner-evidence-oct06/seal-6f5'
P = SEAL / 'publication-candidates'
TREE = OUT.parent / 'm63-broker-control-owner-oct06'
BASE = '68a280b9cf251bbf79c2ca188ac8b4aefe7562e0'
FINAL = '6f5de88935c6ff7a79a87cf5440cc47f86fb0d10'
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*a): return subprocess.check_output(['git', '-C', str(TREE), *a])
def put(n, d): (OUT/n).write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
def tree_map(head):
    result = {}
    for row in git('ls-tree', '-r', '-z', head).split(b'\0'):
        if not row: continue
        meta, path = row.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        result[path.decode()] = (mode, kind, blob)
    return result

assert sha((SEAL/'SAFE_CANDIDATES.json').read_bytes()) == '3dc4c4e91ca8b3932518310b3feb36cfb8d15c517a255a947c33850c3d5fb0bf'
assert sha((SEAL/'READBACK.json').read_bytes()) == '59dec9d56994a6a8ad7a11ebbcf80a945df0d0528f34262b5247a289e26f27c6'
manifest = json.loads((SEAL/'SAFE_CANDIDATES.json').read_bytes())
assert manifest['fixed_head'] == FINAL
rows = []
for e in manifest['entries']:
    path = Path(e['candidate_path'])
    assert not path.is_absolute() and '..' not in path.parts
    b = (P/path).read_bytes()
    assert len(b) == e['candidate_size'] and sha(b) == e['candidate_sha256']
    original = Path(e['raw_path']).read_bytes()
    assert len(original) == e['raw_size'] and sha(original) == e['raw_sha256']
    transform = e['transformation']
    if transform == 'identity': assert b == original
    else:
        assert transform == 'literal_home_prefix_to_tilde'
        assert b == original.replace(b'$HOME', b'~')
    b.decode('utf-8')
    rows.append({k:e[k] for k in ('candidate_path','candidate_size','candidate_sha256','transformation')})
assert len(rows) == 98 == len({r['candidate_path'] for r in rows})
assert sum(r['candidate_size'] for r in rows) == manifest['total_bytes'] == 17189106
maps, cache = {}, {}
for head in json.loads((P/'SOURCE_BINDINGS.json').read_bytes())['heads']:
    m = json.loads((P/'git-inputs'/f'{head}.json').read_bytes())
    actual = {p:v for p,v in tree_map(head).items() if not p.startswith('progress/')}
    assert m['head'] == head and m['tree'] == git('rev-parse', head+'^{tree}').decode().strip()
    assert len(actual) == m['count'] == len(m['entries']) == len({e['path'] for e in m['entries']})
    for e in m['entries']:
        assert actual[e['path']] == (e['mode'],e['type'],e['blob'])
        if e['blob'] not in cache: cache[e['blob']] = git('cat-file','blob',e['blob'])
        b = cache[e['blob']]
        assert len(b) == e['size'] and sha(b) == e['sha256']
    maps[head] = m
assert len(maps) == 8 and sum(m['count'] for m in maps.values()) == 12447 and len(cache) == 1552
base = {e['path']:e for e in maps[BASE]['entries']}
final = {e['path']:e for e in maps[FINAL]['entries']}
changed = sorted(p for p in base if base[p] != final[p])
assert changed == ['services/api/app/application/codex_turn.py','services/api/app/application/codex_turn_worker.py','services/api/app/infrastructure/codex_turn_repository.py']
assert len(final) == 1558 and len(set(final)-set(base)) == 5
assert all(tree_map(FINAL)[p] == v for p,v in tree_map(BASE).items() if p.startswith('progress/'))
assert git('rev-parse','HEAD').decode().strip() == FINAL and not git('status','--porcelain').strip()
for e in final.values(): assert (TREE/e['path']).read_bytes() == cache[e['blob']]
for e in json.loads((P/'SOURCE_BINDINGS.json').read_bytes())['source_copies']:
    assert (P/e['candidate']).read_bytes() == cache[e['blob']]

runner = Path(next(e['raw_path'] for e in manifest['entries'] if e['candidate_path']=='run_stage.py')).read_bytes()
runner_sha = sha(runner)
assert runner_sha == 'e971ebf919683f78c171a8bebc0931e23d0b462fa87b745db7474726f34a1d32'
stages = []
for row in json.loads((P/'STAGE_HISTORY.json').read_bytes()):
    s, receipt, command = row['stage'], row['receipt'], row['command']
    assert receipt == json.loads((P/s/'receipt.json').read_bytes())
    assert command == json.loads((P/s/'command.json').read_bytes())
    assert json.loads((P/s/'before.json').read_bytes()) == json.loads((P/s/'after.json').read_bytes()) == maps[receipt['head']]
    assert receipt['head'] == command['source_head'] and receipt['before_after_complete_exact']
    assert receipt['runner_sha256'] == command['runner_sha256'] == runner_sha
    if row['admitted_log'] == 'run.log':
        entry = next(e for e in manifest['entries'] if e['candidate_path'] == s+'/run.log')
        assert entry['raw_sha256'] == receipt['log_sha256'] and entry['raw_size'] == receipt['log_size']
    else:
        assert row['admitted_log'] == 'BOUNDED_FAILURE.json' and receipt['command_exit_code'] == 1
        selection = json.loads((P/s/'BOUNDED_FAILURE.json').read_bytes())
        # Complete failed logs remain excluded; only original digests and selected error lines are admitted.
        assert receipt['log_sha256'] in json.dumps(selection) and str(receipt['log_size']) in json.dumps(selection)
    if receipt['head'] == FINAL: assert receipt['command_exit_code'] == receipt['wrapper_exit_code'] == 0
    stages.append(row)
assert len(stages) == 15 and sum(r['receipt']['input_count']*2 for r in stages) == 46716
assert len([s for s in stages if s['receipt']['head'] == FINAL]) == 7
assert b'22 passed, 2 warnings' in (P/'expanded-focused-02/run.log').read_bytes()
assert b'473 passed, 3 warnings' in (P/'related-final-01/run.log').read_bytes()
binding = json.loads((P/'RED_GREEN_TEST_BINDING.json').read_bytes())
red_test = git('show',binding['red_head']+':tests/integration/test_codex_broker_control_owner.py')
assert red_test == git('show',binding['green_head']+':tests/integration/test_codex_broker_control_owner.py')
assert len(red_test) == binding['size'] and sha(red_test) == binding['sha256']
put('READBACK.json', {
    'role':'root independent fixed source Spec/Standards and exact original evidence qualification; no rerun',
    'fixed_base':BASE,'fixed_source':FINAL,'candidates':rows,'candidate_count':98,'candidate_bytes':17189106,
    'git_maps':8,'git_bindings':12447,'distinct_git_blobs':1552,'actual_live_complete_inputs':1558,
    'stage_count':15,'stage_map_bindings':46716,'stages':stages,'old_unchanged_engineering':1550,
    'changed_prior_paths':changed,'new_paths':sorted(set(final)-set(base)),'original_complete_test_red_green_identical':True,
    'source_review':{'standards_P1_P2':0,'spec_P1_P2':0,'sole_norm_sha256':'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec',
      'read_scope':'Full new modules/models/repository/migration, three prior-source deltas, whole384line final test; caller transaction and original worker callback context',
      'conclusions':['forward0036 and privatev7 witnesses are permitted by20.17.5/20.17.7; v1-v6/core54/0001 unchanged',
      'HTTP only prepares stop intent; possible-send commits before peer frames outside transaction; duplicate keys do not resend',
      'current synthetic callback/lease/Bootstrap upstream thread mapping checked; local randomSessionAnchor is never upstream identity',
      'full head/member/record/witness and provider-start integrity checked; raw rejected frames retained; emptyACK never local terminal',
      'default production proof/protocol/runtime qualification remains closed; explicit callback pump only']},
    'limits':['complete failed logs not read/admitted; exact original digests and selected failure lines only',
      'pure synthetic peer association has no actual native turn/start receipt or production mapping',
      '22 focused and473 related overlap historical subsets; not additive coverage',
      'whole Python/Web/native/CI for6f source NOT_RUN; running68a whole gate cannot qualify these new source changes',
      'M6.3/AC21/M7 NOT_ACCEPTED; no physical cleanup proof, real IPC/model/tool qualification or release',
      'no source/remote mutation, model/network/runtime credential access or host probe in verification']})
print(json.dumps({'status':'PASS','source':FINAL,'candidates':98,'engineering_inputs':1558,'fixed_final_gates':7,'readback_sha256':sha((OUT/'READBACK.json').read_bytes())}))
