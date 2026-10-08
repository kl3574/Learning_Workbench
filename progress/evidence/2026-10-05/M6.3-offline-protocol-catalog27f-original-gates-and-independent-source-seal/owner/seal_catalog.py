"""Documentary owner sealing of fixed catalog source and finite actual gates."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = ROOT.parent / 'm63-turn-protocol-catalog-oct05'
SEAL = ROOT / 'seal-27f'
BASE = '8b8699d3aad45180ab3b339ea60979c1478f0b92'
FINAL = '27f549ff5a8fd67b0a601b67a5ba51ef35f6765f'
HEADS = [BASE, '5364926fc40171a0bad19b04c851eac0b7fce0b9', '4500432d2f119da2a8e6dd41024ab9d94db9feed',
         '30ab7f8f620b1a00b97fa97fb0681e87a868b23e', '8a0f19eccc3cd93689fd3223eb5be31ac06ee048',
         '387916827f855f5973656ed03c179ac520d267bf', FINAL]
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def js(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()

def git(*args):
    return subprocess.check_output(['git', '-C', str(TREE), *args])

def load(path):
    return json.loads(path.read_text())

assert not SEAL.exists()
assert git('rev-parse', 'HEAD').decode().strip() == FINAL and git('status', '--porcelain') == b''
cache = {}
maps = []
for head in HEADS:
    entries = []
    for row in git('ls-tree', '-r', '-z', head).split(b'\0'):
        if not row:
            continue
        meta, path = row.split(b'\t', 1)
        path = path.decode()
        if path.startswith('progress/'):
            continue
        mode, kind, blob = meta.decode().split()
        assert kind == 'blob'
        if blob not in cache:
            cache[blob] = git('cat-file', 'blob', blob)
        raw = cache[blob]
        entries.append(dict(path=path, mode=mode, type=kind, blob=blob, size=len(raw), sha256=sha(raw)))
    maps.append({'head': head, 'tree': git('rev-parse', head + '^{tree}').decode().strip(),
                 'count': len(entries), 'entries': entries})
by_head = {m['head']: m for m in maps}
old = {e['path']: e for e in maps[0]['entries']}
new = {e['path']: e for e in maps[-1]['entries']}
delta = sorted(p for p in set(old) | set(new) if old.get(p) != new.get(p))
assert len(delta) == 14 and all(p not in old for p in delta)
assert len(old) == 1527 and len(new) == 1541 and all(old[p] == new[p] for p in old)
assert new['PRODUCT_DESIGN.md']['sha256'] == SPEC
for entry in new.values():
    assert (TREE / entry['path']).read_bytes() == cache[entry['blob']]
test_path = 'tests/unit/test_codex_turn_protocol_catalog.py'
first_red = next(e for e in by_head[HEADS[1]]['entries'] if e['path'] == test_path)
first_green = next(e for e in by_head[HEADS[2]]['entries'] if e['path'] == test_path)
typed_red = next(e for e in by_head[HEADS[4]]['entries'] if e['path'] == test_path)
typed_green = next(e for e in by_head[HEADS[5]]['entries'] if e['path'] == test_path)
assert first_red == first_green and typed_red == typed_green
prod_delta = git('diff', '--numstat', HEADS[2], FINAL, '--',
                 'services/api/app/application/codex_turn_protocol_models.py',
                 'services/api/app/infrastructure/codex_turn_protocol_catalog.py').decode().strip()
assert prod_delta == '2\t0\tservices/api/app/infrastructure/codex_turn_protocol_catalog.py'

runner_sha = sha((ROOT / 'run_stage.py').read_bytes())
stages = sorted(p.name for p in ROOT.iterdir() if p.is_dir() and (p / 'receipt.json').is_file())
assert len(stages) == 15
stage_rows = []
for stage in stages:
    p = ROOT / stage
    receipt, command = load(p / 'receipt.json'), load(p / 'command.json')
    before, after = load(p / 'before.json'), load(p / 'after.json')
    raw = (p / 'run.log').read_bytes()
    assert before == after == by_head[receipt['head']]
    assert receipt['before_after_complete_exact'] is True and receipt['input_count'] == before['count']
    assert command['source_head'] == receipt['head'] and command['cwd'] == str(TREE)
    assert command['runner_sha256'] == receipt['runner_sha256'] == runner_sha
    assert len(raw) == receipt['log_size'] and sha(raw) == receipt['log_sha256']
    assert receipt['command_exit_code'] == receipt['wrapper_exit_code']
    assert (receipt['command_exit_code'] != 0) == (stage in {'packaged-source-red', 'expanded-focused-02', 'ruff-01', 'mypy-01'})
    match = re.search(r'^\d+ (?:failed, \d+ passed|failed|passed)[^\n]*$', raw.decode(), re.M)
    summary = match[0] if match else raw.decode().strip()
    stage_rows.append({**receipt, 'summary': summary,
                       'command_sha256': sha((p / 'command.json').read_bytes()),
                       'before_sha256': sha((p / 'before.json').read_bytes()),
                       'after_sha256': sha((p / 'after.json').read_bytes())})
bindings = sum(2 * row['input_count'] for row in stage_rows)
assert bindings == 46204

# Re-read only the explicitly authorized source receipts and selected originals.
source_root = ROOT.parent / 'm63-app-server-protocol-recon-oct03'
raw_receipt = (source_root / 'receipt.json').read_bytes()
assert len(raw_receipt) == 55893 and sha(raw_receipt) == 'b64f43cd1b5a7024bcdcb421292cef93b61721ba76a4f325e7663be93931cd9c'
receipt = json.loads(raw_receipt)
receipt_entries = {e['path'].removeprefix('schemas/'): e for e in receipt['files']}
prefix = 'services/api/app/infrastructure/codex_turn_protocol/'
projection_entry = new[prefix + 'source-receipt.json']
projection_raw = cache[projection_entry['blob']]
projection = json.loads(projection_raw)
assert b'/home/' not in projection_raw and 'command' not in projection
assert projection['original_receipt_sha256'] == sha(raw_receipt)
assert projection['original_receipt_size'] == len(raw_receipt)
for field, original in [('historical_cli_version', 'version'), ('historical_binary_sha256', 'binary_sha256'),
                        ('historical_generated_files', 'generated_files'), ('historical_exit_code', 'exit'),
                        ('historical_generated_at', 'at')]:
    assert projection[field] == receipt[original]
schema_bindings = []
for member in projection['selected_files']:
    original = (source_root / 'schemas' / member['path']).read_bytes()
    e = new[prefix + member['path']]
    assert original == cache[e['blob']]
    assert member['size'] == len(original) == receipt_entries[member['path']]['bytes']
    assert member['sha256'] == sha(original) == receipt_entries[member['path']]['sha256']
    assert member['sha256'] in git('show', FINAL + ':PRODUCT_DESIGN.md').decode()
    schema_bindings.append({'path': member['path'], 'size': len(original), 'sha256': sha(original),
                            'git_blob': e['blob'], 'receipt_entry_exact': True})
assert sum(e['size'] for e in schema_bindings) == 93287
source_binding = {'role': 'owner documentary source qualification, not independent review',
                  'base': BASE, 'final': FINAL, 'owned_paths': delta, 'final_input_count': 1541,
                  'unchanged_all_old_inputs': 1527, 'source_map_count': 7,
                  'source_bindings': sum(m['count'] for m in maps), 'distinct_blobs': len(cache),
                  'first_red_green_whole_test_bytes_equal': True, 'first_test_binding': first_red,
                  'typed_red_green_whole_test_bytes_equal': True, 'typed_test_binding': typed_red,
                  'production_delta_from_first_implementation': prod_delta,
                  'source_original_selected_bindings': schema_bindings,
                  'source_raw_receipt': {'size': len(raw_receipt), 'sha256': sha(raw_receipt),
                                         'not_admitted_to_public_source_or_candidate_contents': True},
                  'public_projection_binding': projection_entry,
                  'public_projection_claim': 'Manually checked historical selected-nine source summary; not full raw receipt reread at runtime/current binary/other305 qualification',
                  'sole_spec_sha256': SPEC, 'final_live_git_all_exact': True, 'final_clean': True}

report = f'''# M6.3 已核验离线目录与有限 wire codec — 作者交付

固定HEAD `{FINAL}`，base `{BASE}`，14个新增路径/4,410+（models192行、catalog88行、test247行、manifest/非秘密来源摘要及9个原schema）。原1,527工程输入全部 mode/type/blob/size/SHA保持，最终1,541完整输入；规范v3.0.15 SHA `{SPEC}`不变。§20.17.1.1/.1.2/.7/.8/.9范围内的内部模块，无新HTTP、无生产注册、无执行。

## 实际实现

`read_catalog/verify_catalog`返回严格 `OfflineTurnProtocolCatalog`，scope=selected9_schema_shapes_only，implemented严格false（0/0.0/True拒绝）。九成员要求精确原顺序/路径/size/hash，保存完整原raw UTF-8字节；97个内部ref全部local解析，不外部fetch/扩展refs。不允许剩余成员自洽掩盖尾删/全删/重复/乱序；原件和source-summary破坏均failclosed，坏读不补文件。

九原schema共93,287字节，逐字等于规范固定314非experimental来源和receipt相应条目。来源摘要是2,101字节closed/versioned人工核验投影（SHA a31441996822a75015aed858c104e9f82039de88bbeca66d8308bef5fc24af27），只标历史原receipt size/SHA、CLI/binary/profile/count/exit/time及九bindings。原55,893字节receipt含私有物理paths/argv，保持私有；未进Git或候选content。runtime read只是核摘要及九原schema，不称完整rawreceipt/currentbinary/其余305原件再验。规范所列binary SHA是历史source事实，不是当前环境/部署保证。另一experimental源三schema不同已独立分析，未替换此bundle。

有限codec：TurnInterruptParams仅支持严格threadId+turnId的owned-free形状（mapping/typed/严格JSONbytes或text），构造规范params字节；command/file_change响应只支持原schema合法decline/cancel。raw重复key、非有限数、surrogate、数字/bool当字符串、蛇形别名/extra拒绝；typed对象强制破坏后再次按真实wire别名严格核验。accept/acceptForSession/policy-amendment/permission/unknown kind不由codec开放。

这些字节不是完整RPC envelope，没有callback id/真实owned session/turn映射或任何传输许可，不证明已发拒绝/中断或远端停机。九schema只有所列参数/审批/一种patch通知，仍缺完整实际使用响应/通知配对、hidden finalrequest InputProof、deployment/session/profile/资源和单次外发强制资格。生产默认main/ProofRegistry空/executorNone、495v4与所有旧bootstrap/Provider/ACK/HTTP/54core/0001/依赖/CI预算均逐字不改。

## 真实失败与门禁

536 test-only原27行实际packaged-source-red 1FAIL（行7实际缺规范目录manifest）；450实现后同完整27行文件/同命令1PASS，不是collection或工具链失败。新增typed输入用例8a实际1FAIL/65PASS：Pydantic always-revalidate把内存Python字段名误当wire别名。387仅catalog函数2+，typed对象先model_dump(by_alias=True)再同closed校验；同8a完整239行test文件/同命令66PASS。27最终只新增两个forcedtypedmutation负例，生产models/schema/摘要未变化。

Ruff-01原F401 unused-import FAIL保留；后新增真实typed使用消除unused，并把弃用的instance.model_fields访问改成class。mypy-01是作者多余指定两目录的错误invocation，exit2/重复模块名，未进入production类型检查；未改config/依赖，按原repo配置noarg mypy-configured-01实际290files PASS。两次行为FAIL及两个静态invocationFAIL原件不追改。

固定最终27实际命令与资格：

| Stage | 终态 | 实际范围 |
|---|---|---|
| focused-final | 68PASS/pytest0.32s、wrapper0.503285s | 新源/codec test全部68；1 warning为故意forcedtyped bool损坏的serializer warning后拒绝 |
| related-final | 186PASS/pytest27.12s、wrapper27.523618s | 明确3文件：v4真实HTTP/SQLite准备、Provider synthetic profile、既有Codex DTO |
| ruff-final | command/wrapper0 | ruff check .，整个项目invocation |
| mypy-final | command/wrapper0 | repo配置noarg mypy，290 sourcefiles |
| spec-final | command/wrapper0 | M0结构/完整性checker，非产品/真实模型验收 |
| generated-final | command/wrapper0 | checked82 artifacts，旧生成品全部不变 |
| diff-final | command/wrapper0 | 8b→HEAD git diff --check |

68覆盖：精确source/字节/hash/member/source投影、尾删/全删/重复/乱序/未知path与字段、bad source/byte/重复JSON/数字bool别名、forced nested/typed对象破坏、严格有限wire与各种许可扩张拒绝、local ref缺失/外部/坏转义/数组及cycle有限解析。一个明确专项用例真实patch并断言process、bootstrap freeze/validity/execute、probe、synthetic model-transport六named seams各0，只覆盖该case的实际catalog读/核/codec调用；不是所有测试的物理监控。模块不读SecretStore/userconfig、不写SQLite或启动Job/worker；相关测试沿既有明确synthetic fixture，不称全部setup0或真实模型。

离线uv sync首次本地37已锁定依赖安装是tool stdout记录，仅配置准备，不当产品测试或host能力探针。无新全4,341/全Web/native/真实CLI/model门禁，旧CI/整体验收事实不借入或改写。

## 原件与共享范围

7固定Git图/10,760 sourcebindings，distinctblob按SOURCE_BINDING原实际值；最终1,541 live bytes/Git全部exact且clean。15阶段/30 fullmaps/46,204 sourcebindings、原command/receipt/log size/SHA和immutable Git前后全exact。两组同完整test原件分别绑定first27行、typed239行。作者自身封存不是独立review，root审查另记录。

SAFE_CANDIDATES逐项准读publication-candidates与outer SAFE/READBACK。候选仅原metadata/fullmaps、安全原logs、固定Git源码/首次两原testbytes、作者source/gate报告与封存脚本；全部identity或明确新documentary记录，不递归准读原DB/ZIP/profile/临时目录/私有完整receipt。原rawreceipt只hash/size来源声明。

生产InputProof/protocol/runtime仍未注册，typed catalog严格false。真实App Server/model/tool/network NOT_RUN；当前账号/资源/隔离环境NOT_EXAMINED，不能默认unavailable推出ENV阻塞。整体M6.3/M7仍NOT_ACCEPTED。本地candidate未merge/push/远端修改；下一步由root独立固定source/候选读回，再决定normal本地整合，真执行资格仍另验。
'''

owner = {'role': 'Implementation owner readback, not independent review or rerun', 'base': BASE, 'final': FINAL,
         'source': source_binding, 'stage_count': 15, 'stage_map_count': 30, 'stage_source_bindings': bindings,
         'stage_rows': stage_rows, 'qualification': {'focused': '68 PASS', 'related': '186 PASS across 3 explicit files',
         'final_static_stages': 5, 'catalog_implemented': False, 'production_registry_executor': 'unchanged empty/None',
         'real_model_cli_tools_network': 'NOT_RUN', 'current_environment': 'NOT_EXAMINED',
         'whole_M63_M7': 'NOT_ACCEPTED', 'canonical_remote_changes': 'NONE'},
         'zero_named_seams': {'scope': 'only test_catalog_and_codec_zero_execution_seams actual case',
                             'names': ['process', 'freeze', 'validity', 'bootstrap', 'probe', 'model_transport'],
                             'counts': [0, 0, 0, 0, 0, 0], 'evidence': 'source assertions + actual focused68PASS',
                             'not_all_tests_or_physical_monitoring': True}}

SEAL.mkdir()
CANDIDATES = SEAL / 'publication-candidates'
CANDIDATES.mkdir()
entries = []
def put(name, raw, origin):
    path = CANDIDATES / name
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists()
    path.write_bytes(raw)
    assert path.read_bytes() == raw
    entries.append({'candidate_path': name, 'candidate_size': len(raw), 'candidate_sha256': sha(raw),
                    'raw_size': len(raw), 'raw_sha256': sha(raw), 'transformation': 'identity', 'origin': origin})

for stage in stages:
    for name in ['command.json', 'receipt.json', 'before.json', 'after.json', 'run.log']:
        p = ROOT / stage / name
        put(stage + '/' + name, p.read_bytes(), {'type': 'original_actual_gate_file', 'source': str(p)})
for path in delta:
    e = new[path]
    put('source/' + path, cache[e['blob']], {'type': 'immutable_git_blob', 'head': FINAL, **e})
for name, e, refs in [('first-red-green.py', first_red, HEADS[1:3]), ('typed-red-green.py', typed_red, HEADS[4:6])]:
    put('source-original-tests/' + name, cache[e['blob']], {'type': 'immutable_git_blob', 'heads': refs, **e})
put('REPORT.md', report.encode(), {'type': 'new_owner_documentary_report'})
put('SOURCE_BINDING.json', js(source_binding), {'type': 'new_owner_git_and_manual_source_provenance_readback'})
put('FULL_GIT_INPUTS.json', js({'maps': maps, 'total_bindings': sum(m['count'] for m in maps), 'distinct_blobs': len(cache)}),
    {'type': 'new_documentary_fixed_git_full_maps'})
put('OWNER_GATE_READBACK.json', js(owner), {'type': 'new_owner_actual_gate_readback'})
put('run_stage.py', (ROOT / 'run_stage.py').read_bytes(), {'type': 'original_fixed_actual_gate_runner', 'sha256': runner_sha})
put('seal_catalog.py', Path(__file__).read_bytes(), {'type': 'new_owner_documentary_seal_script'})

patterns = {'provider_key_shape': rb'\bsk-[A-Za-z0-9_-]{16,}',
            'private_key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
            'actual_cookie_line': rb'(?im)^(?:set-cookie|cookie):\s*\S+'}
hits = []
for e in entries:
    raw = (CANDIDATES / e['candidate_path']).read_bytes()
    raw.decode('utf-8')
    for label, pattern in patterns.items():
        if re.search(pattern, raw):
            hits.append({'path': e['candidate_path'], 'label': label})
assert not hits, hits
content = {'role': 'owner finite candidate content assessment, independent readback pending root',
           'stage_metadata': 'fixed-source paths/SHA/times/command/exit only; no auth/session runtime payload',
           'all15_original_logs': 'read completely: ordinary pytest source assertion/revalidation static fixture failures, Ruff/mypy diagnostics/summaries; no actual business JSON/cookies/CLI/tool body',
           'source': '14 immutable source originals, 9 upstream fixed public schemas and path-free manually checked provenance projection; no private raw receipt',
           'docs_scripts_maps': 'read bounded documentary content only, full immutable engineering source metadata; no runtime directory admission',
           'bounded_scanner_patterns': list(patterns), 'bounded_scanner_hits': hits,
           'limits': 'Exact candidate admission only, not a blanket DLP or host security assurance'}
put('CANDIDATE_CONTENT_REVIEW.json', js(content), {'type': 'new_owner_finite_content_review'})
manifest = {'scope': 'Only exact publication-candidates and two outer metadata files are admitted; no recursive private runtime/source receipt read',
            'base': BASE, 'final': FINAL, 'candidate_base': str(CANDIDATES), 'candidate_count': len(entries),
            'entries': entries, 'outer_metadata': ['SAFE_CANDIDATES.json', 'READBACK.json'],
            'excluded': 'All unlisted files, private full historical raw receipt, DB/ZIP/profile/secret/runtime/temp directories'}
(SEAL / 'SAFE_CANDIDATES.json').write_bytes(js(manifest))
readback = {'role': 'owner exact candidate/Git/source/gate readback, not independent review or product rerun',
            'final': FINAL, 'candidate_count': len(entries), 'candidate_total_bytes': sum(e['candidate_size'] for e in entries),
            'manifest_sha256': sha((SEAL / 'SAFE_CANDIDATES.json').read_bytes()), 'all_candidate_size_sha_exact': True,
            'all_entries_identity': True, 'source_maps': 7, 'source_bindings': sum(m['count'] for m in maps),
            'distinct_source_blobs': len(cache), 'stage_maps': 30, 'stage_bindings': bindings,
            'unchanged_old_inputs': 1527, 'final_live_git_exact_clean': True,
            'report_sha256': sha((CANDIDATES / 'REPORT.md').read_bytes()),
            'raw_source_receipt_admission': 'EXCLUDED; summary qualified manually, selected9 source only',
            'production_qualification': 'unregistered/unavailable', 'real_cli_model': 'NOT_RUN',
            'canonical_remote_changes': 'NONE', 'root_independent_review': 'separate pending seal readback'}
(SEAL / 'READBACK.json').write_bytes(js(readback))
for e in entries:
    raw = (CANDIDATES / e['candidate_path']).read_bytes()
    assert len(raw) == e['candidate_size'] and sha(raw) == e['candidate_sha256']
assert git('status', '--porcelain') == b'' and git('rev-parse', 'HEAD').decode().strip() == FINAL
print(json.dumps({'seal': str(SEAL), 'candidates': len(entries), 'safe_sha256': sha((SEAL / 'SAFE_CANDIDATES.json').read_bytes()),
                  'readback_sha256': sha((SEAL / 'READBACK.json').read_bytes()), 'report_sha256': sha((CANDIDATES / 'REPORT.md').read_bytes()),
                  'source_maps': 7, 'source_bindings': sum(m['count'] for m in maps), 'distinct_blobs': len(cache),
                  'stage_maps': 30, 'stage_bindings': bindings, 'final': FINAL}))
