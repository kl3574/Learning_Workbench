"""Owner-only documentary sealing. No product tests or runtime probes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = ROOT.parent / 'm63-production-preparation-closure-oct05'
SEAL = ROOT / 'seal-495'
FINAL = '495e4daddddb64460326659be5af341085654131'
BASE = '6671dd5c924edbac8ca7f479c4f51d4afec14480'
RUNNER = 'f401ba02d01743114a8ee754ba2aa2a8cf45fb7a8fcfa4608610535737da6c98'
SPEC = 'b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec'

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def read_json(p: Path):
    return json.loads(p.read_text())

def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(TREE), *args])

def js(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()

assert not SEAL.exists(), 'Refuse overwrite of a prior seal'
assert git('rev-parse', 'HEAD').decode().strip() == FINAL
assert git('status', '--porcelain') == b''
source = read_json(ROOT / 'SOURCE_BINDING_V2.json')
full = read_json(ROOT / 'FULL_GIT_INPUTS_V2.json')
maps = {m['head']: m for m in full['maps']}
assert len(maps) == 7 and full['total_bindings'] == 10686
assert source['final_input_count'] == 1527
blob_cache: dict[str, bytes] = {}
for m in maps.values():
    expected = []
    for row in git('ls-tree', '-r', '-z', m['head']).split(b'\0'):
        if not row:
            continue
        header, raw_path = row.split(b'\t', 1)
        path = raw_path.decode()
        if path.startswith('progress/'):
            continue
        mode, kind, blob = header.decode().split()
        assert kind == 'blob'
        if blob not in blob_cache:
            blob_cache[blob] = git('cat-file', 'blob', blob)
        raw = blob_cache[blob]
        expected.append(dict(path=path, mode=mode, type=kind, blob=blob,
                             size=len(raw), sha256=sha(raw)))
    assert m['entries'] == expected and m['count'] == len(expected)
    assert m['tree'] == git('rev-parse', m['head'] + '^{tree}').decode().strip()
assert len(blob_cache) == 1516
for e in maps[FINAL]['entries']:
    assert (TREE / e['path']).read_bytes() == blob_cache[e['blob']]
assert sha((ROOT / 'run_stage.py').read_bytes()) == RUNNER

stages = sorted(p.name for p in ROOT.iterdir() if p.is_dir() and (p / 'receipt.json').is_file())
assert len(stages) == 19
gate_rows = []
map_bindings = 0
for stage in stages:
    folder = ROOT / stage
    cmd, receipt = read_json(folder / 'command.json'), read_json(folder / 'receipt.json')
    before, after = read_json(folder / 'before.json'), read_json(folder / 'after.json')
    raw = (folder / 'run.log').read_bytes()
    assert before == after == maps[receipt['head']]
    assert receipt['input_count'] == before['count']
    assert receipt['before_after_complete_exact'] is True
    assert cmd['source_head'] == receipt['head'] and cmd['cwd'] == str(TREE)
    assert cmd['runner_sha256'] == receipt['runner_sha256'] == RUNNER
    assert receipt['log_size'] == len(raw) and receipt['log_sha256'] == sha(raw)
    assert receipt['command_exit_code'] == receipt['wrapper_exit_code']
    assert (receipt['command_exit_code'] != 0) == (stage in {'first-behavior-red', 'mypy-01', 'ruff-final'})
    if stage == 'first-behavior-red':
        result = '1 pytest FAIL; expected v4, observed v1; full raw log excluded'
    elif stage == 'mypy-01':
        result = '1 static invocation FAIL containing 3 union-attr diagnostics'
    elif stage == 'ruff-final':
        result = '1 static invocation FAIL containing F401 unused import'
    elif re.search(r'^\d+ passed,.*$', raw.decode(), re.M):
        result = re.search(r'^\d+ passed,.*$', raw.decode(), re.M)[0]
    else:
        result = raw.decode().strip()
    gate_rows.append({**receipt, 'result': result, 'command_sha256': sha((folder / 'command.json').read_bytes()),
                      'before_sha256': sha((folder / 'before.json').read_bytes()),
                      'after_sha256': sha((folder / 'after.json').read_bytes())})
    map_bindings += before['count'] + after['count']
assert map_bindings == 58024
seam_readback = []
for stage in ['focused-final-01', 'focused-final-02']:
    p = ROOT / stage / 'case-receipts.jsonl'
    rows = [json.loads(line) for line in p.read_text().splitlines()]
    assert len(rows) == 18 and len({r['test'] for r in rows}) == 18
    for row in rows:
        assert set(row['counts']) == {'freeze', 'validity', 'bootstrap', 'process', 'probe', 'secret_read',
                                     'model_executor', 'model_transport', 'tool'}
        assert all(type(v) is int and v == 0 for v in row['counts'].values())
        assert row['synthetic_bootstrap_setup_calls'] == 1
        assert row['scope'] == 'new unavailable phase after separately declared synthetic setup'
    seam_readback.append({'stage': stage, 'rows': 18, 'counters': 162, 'all_zero': True,
                          'sha256': sha(p.read_bytes()), 'scope': rows[0]['scope'],
                          'setup_note': 'Each row has 1 synthetic bootstrap setup call. The two history cases additionally complete 2 memory protocol peer calls before the counted phase.'})

red_lines = (ROOT / 'first-behavior-red/run.log').read_bytes().splitlines(keepends=True)
selected = list(range(25, 34)) + [45, 46]
excerpt = b''.join(red_lines[i - 1] for i in selected)
assert b"assert 'codex-turn-context-v1' == 'codex-turn-context-v4'" in excerpt

report = f'''# M6.3 不可执行准备原件闭包 v4 — 作者交付报告

固定源码 `{FINAL}`，base `{BASE}`；6 路径 587+/20-（5 个生产 Python 路径和一个 439 行 integration test）。唯一规范 PRODUCT_DESIGN v3.0.15 SHA `{SPEC}`，本切片仅落实 §20.17.1.1、§20.17.1.2、§20.17.7 的已有准备/持久读回/严格原件与失败关闭边界；不补写规范或新 HTTP 合同。

## 实际行为与资格

新的默认不可执行 TurnInput v1 准备使用严格私有 `UnavailablePreparationContext` v4。它冻结真实受检 BootstrapSnapshot（完整描述与原 receipt）及其 digest、当次 ProviderConfigView 非秘密版本事实、当次教材/证据/历史 pair 来源，存入实际 SQLite 事务。通过 bootstrap owner 既有 `checked_owned_sessions` 接口核对原件，Context/Provider 既有 read/verify 对整个 v4 记录与历史 pair 做原件一致性核验。

严格 `implemented=false` 拒绝整数 0、浮点 0.0 和 True。缺项是闭合有序三项：`production_input_proof_unregistered`、`production_turn_protocol_unregistered`、`production_turn_runtime_unregistered`；不填造 turn schema/init/resume/final request/deployment/资源事实，不把准备闭包称完整生产 InputProof 或真正 turn freeze。生产 registry 仍空，executor 仍 None；现有 preview 仍 503/CODEX_INPUT_PROOF_UNAVAILABLE，无 proposal/外发许可/排队/执行。

历史 bootstrap actor 与原 turn actor 按各 owner 原事实比较；不要求当前合法读者等于旧 actor。Provider config/secret 元数据版本或教材 revision 合法推进投影为原有 changed/current 资格，原 ACK、hash、Context 不回写。原件破坏 409 失败关闭，GET 不修复、不新增表写。事务中 Context/Run/command 任一点真实 SQLite abort 均整体回滚，不留下局部准备。

旧 TurnInput/runtime v1、context v1/v2/v3、原事件/ACK decoder、54 core、0001 baseline、Bootstrap/public DTO/路由/依赖/CI预算均保持原字节。旧合成可执行 v2 与旧不可执行 v1/v3不被新准备升级。

## 原始测试与失败记录

首次 test-only 7c1058 实际 1 FAIL：真实 HTTP 准备的内部 context.version 为 v1，期待 v4。实现 de4d 后同一完整 83 行 test 文件、同样命令实际 1 PASS。两固定 Git 原件的文件 mode/type/blob/size/SHA 完全相同；不是替换 oracle 的 RED→GREEN。

`mypy-01` 是一次静态 invocation FAIL，含 3 条 union-attr diagnostics；`ruff-final` 是一次 F401 unused-import FAIL。三个失败的原 command/receipt/full before-after maps/raw log hash 均保留；mypy 与 Ruff 的完整安全日志列入本包。首次 pytest FAIL 的完整 raw fixture repr 日志不列入候选，只选择原始 1-based 行 25–33、45–46，逐行原字节摘录，完整原日志 SHA 为 `0e4ec41712b3d58bde8df982458c02ea515cb85c4a96191c65d6f87eeb89cc68`（3047 bytes）。原私有 full log不变，不称公开摘录为完整原件。

固定最终 495 上实际 finite gates：

| Stage | 实际终态 | 时间/范围 |
|---|---|---|
| focused-final-02 | 30 PASS | pytest 31.16s，wrapper 31.582882s |
| related-final-02 | 334 PASS | 9 个指定相关文件；pytest 181.63s，wrapper 182.173363s |
| ruff-final-02 | exit/wrapper 0 | 新6路径 |
| mypy-final-02 | exit/wrapper 0 | 288 source files |
| spec-final-02 | exit/wrapper 0 | 仅结构/完整性 M0 checker，非产品验收 |
| generated-final-02 | exit/wrapper 0 | checked 82 artifacts |
| diff-final-02 | exit/wrapper 0 | git diff --check |

30 专项覆盖严格 false/封闭缺项和伪造字段拒绝、完整 bootstrap/Provider/context 损坏与成员尾删、重放/GET 失败关闭、原 SQLite 写回滚、新 actor 权限、Provider config/secret 非秘密版本和 Content revision 合法推进、旧 ACK 字节、既有 context v1/v3 codec 原版本、实际 completed pair retained/omitted 原件核验。334 相关回归是 preparation/consent/dispatch/lifecycle/review/events/Provider/DTO 的明确九文件，使用现有受控内存 fixture，非新的全平台完整门禁。

focused-final-01/02 各18条 payload-free case receipts、各162个 named counters 都为0。它们只覆盖被 fence 的新不可执行阶段（bootstrap freeze/validity/execute、Popen、probe、secret read、model executor/transport、tool）。每案准备 fixture 有1次合成 bootstrap；两个历史案在 fence 前分别完成2次内存 protocol peer 调用。不能称全流程/所有30案/主机物理监控为0。其他严格模型与 codec 用例靠其明确 assertions；related fixtures 中的合成调用不改称真实模型或0调用。

restart 测试使用未 enterlifespan 的 TestClient；仅证明持久读回相同原件、GET/preview无写和对应 named seams，不证明 worker 启动、调度、恢复收敛。legacy v1/v3 两个 codec 原件由既有 context factory 构建，不 rewrite 旧记录；手工 pair 只证明 codec，不能当实际 Provider history授权。实际历史全 pair 验证来自另两个 real HTTP + SQLite +明确 synthetic Provider setup 用例。

## 固定输入与显式共享范围

7 固定 Git 全图：10,686 bindings /1,516 distinct blobs；最终1,527输入；1,521旧非重叠输入 mode/type/blob/size/SHA不变。19原阶段、38个完整 before/after图、58,024 bindings全部与相应 immutable Git及原receipt/log SHA一致，前后实际exact；最终工作树clean且逐1,527 tracked bytes与固定Git相同。首RED图1,526，其余stage1,527。

v2 documentary verifier 修正旧脚本命名 selector `migrations/0001_core.sql` 为实际 `migrations/0001_baseline.sql`，另写新 v2 输出；旧 verifier和原输出不动。原全图已包括真正baseline，故不是源码/门禁结果修正。两 verifier sha/selector差异在独立说明文件。

封包 builder 首次仅 documentary 执行因将 Ruff `All checks passed!` 误判为数字 pytest summary 而 TypeError 退出，尚未创建 seal。原 builder 副本与具名失败记录保留；改为精确数字 summary regex 后再次构建。此为封包脚本解析问题，不是产品门禁 FAIL 或测试重跑；所有19原门禁原件及源码不变。

共享仅 `SAFE_CANDIDATES.json` 逐项列出的 publication-candidates 文件及 outer READBACK/SAFE。所有复制为 identity；原RED摘录只有明确原行选择，无隐式日志净化。排除原完整RED raw log、DB、ZIP、secret directories、runtime/profile/temp与所有未列明文件；不递归授权。候选每项含原/复制 size/SHA、来源及转换，固定源码附Git head/blob provenance。作者检查与封存不是独立 review；root 的 source/evidence独审另外进行。

## 未完成与下一步

本切片不注册生产 InputProof checker、production turn protocol/runtime/executor，不建立真实外发模型/工具或host资源资格。真实 CLI/model/tool/network与生产正路径 NOT_RUN；不存在从默认 unavailable 推导的真实 ENV 能力/安全结论。全4,341后端/全Web/native不在本次 finite gate范围；任何旧完整/CI失败、未知根因或stage进度不回填。整体 M6.3 和 M7均未因此验收。

root 独立逐候选读回后可按已有授权 normal本地融合本切片；作者未merge/push/写远端，canonical和旧封包均不改。后续只读核对已有9上游schema及内部ref闭包/来源收据，准确记录可核原件及 production admission缺项；不借synthetic取得生产资格。
'''

owner_readback = {
    'role': 'Implementation owner evidence qualification, not independent review and not a new product run',
    'base': BASE, 'final': FINAL, 'spec_sha256': SPEC,
    'source_summary': source, 'source_git_maps': 7, 'source_git_bindings': 10686,
    'source_distinct_blobs': 1516, 'stage_count': 19, 'stage_map_count': 38,
    'stage_source_bindings': map_bindings, 'stage_rows': gate_rows, 'seams': seam_readback,
    'red_excerpt': {'original_log_sha256': sha((ROOT / 'first-behavior-red/run.log').read_bytes()),
                    'original_log_size': 3047, 'selected_one_based_lines': selected,
                    'excerpt_sha256': sha(excerpt), 'full_raw_log_not_admitted': True},
    'qualification': {'final_focused': '30 PASS', 'final_related': '334 PASS across 9 explicit files',
                      'final_static_stages': 5, 'real_model_cli_tools': 'NOT_RUN',
                      'production_registry_executor': 'unchanged empty / None',
                      'whole_M63_M7_acceptance': 'NOT_ACCEPTED',
                      'canonical_remote_changes': 'NONE'},
    'source_snapshot': 'All 1527 live tracked non-progress inputs equal final immutable Git; clean at this readback',
}

SEAL.mkdir()
CANDIDATES = SEAL / 'publication-candidates'
CANDIDATES.mkdir()
entries = []
def candidate(path: str, raw: bytes, origin: dict, *, transform: str = 'identity', original: bytes | None = None):
    dest = CANDIDATES / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert not dest.exists()
    dest.write_bytes(raw)
    assert dest.read_bytes() == raw
    orig = raw if original is None else original
    entries.append({'candidate_path': path, 'candidate_size': len(raw), 'candidate_sha256': sha(raw),
                    'raw_size': len(orig), 'raw_sha256': sha(orig), 'transformation': transform,
                    'origin': origin})

for stage in stages:
    for name in ['command.json', 'receipt.json', 'before.json', 'after.json']:
        p = ROOT / stage / name
        candidate(f'{stage}/{name}', p.read_bytes(), {'type': 'original_evidence_file', 'source': str(p)})
    if stage != 'first-behavior-red':
        p = ROOT / stage / 'run.log'
        candidate(f'{stage}/run.log', p.read_bytes(), {'type': 'original_evidence_file', 'source': str(p)})
    else:
        p = ROOT / stage / 'run.log'
        candidate(f'{stage}/bounded-failure-excerpt.log', excerpt,
                  {'type': 'bounded_original_log_lines', 'source': str(p), 'selected_one_based_lines': selected},
                  transform='exact original line selection in listed order, retaining original newlines', original=p.read_bytes())
    if stage in ['focused-final-01', 'focused-final-02']:
        p = ROOT / stage / 'case-receipts.jsonl'
        candidate(f'{stage}/case-receipts.jsonl', p.read_bytes(), {'type': 'original_evidence_file', 'source': str(p)})
for name in ['SEAMS.md', 'run_stage.py', 'verify_source_binding_v2.py', 'FULL_GIT_INPUTS_V2.json',
             'SOURCE_BINDING_V2.json', 'SOURCE_BINDING_SELECTOR_CORRECTION.json']:
    p = ROOT / name
    candidate(name, p.read_bytes(), {'type': 'documentary_source_or_verification', 'source': str(p)})
for name in ['seal_495_v1.py', 'SEAL_BUILDER_FIRST_FAILURE.json']:
    p = ROOT / name
    candidate(name, p.read_bytes(), {'type': 'preserved_documentary_seal_builder_failure', 'source': str(p)})
for path in source['owned_paths']:
    e = next(e for e in maps[FINAL]['entries'] if e['path'] == path)
    candidate('source/' + path, blob_cache[e['blob']], {'type': 'immutable_git_blob', 'head': FINAL, **e})
first = source['fixed_first_red_green_test_binding']
candidate('source-first-red-green/test_codex_unavailable_preparation_closure.py', blob_cache[first['blob']],
          {'type': 'immutable_git_blob', 'heads': ['7c1058f977f33b167036830c315b693cfbae2084',
                                                 'de4d12da56100a6b06c065e41881b69ba0ee8127'], **first})
candidate('REPORT.md', report.encode(), {'type': 'new_owner_report', 'product_execution': False})
candidate('OWNER_GATE_READBACK.json', js(owner_readback), {'type': 'new_documentary_readback', 'product_execution': False})
candidate('seal_495.py', Path(__file__).read_bytes(), {'type': 'new_owner_documentary_sealing_script', 'source': str(Path(__file__))})

# Bounded lexical checks supplement the owner's content read; not a global DLP claim.
patterns = {
    'provider_key_shape': rb'\bsk-[A-Za-z0-9_-]{16,}',
    'authorization_value': rb'(?i)authorization[\"\']?\s*[:=]\s*[\"\']bearer\s+[A-Za-z0-9_-]{16,}',
    'private_key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'actual_cookie_line': rb'(?im)^(?:set-cookie|cookie):\s*\S+',
}
hits = []
for entry in entries:
    b = (CANDIDATES / entry['candidate_path']).read_bytes()
    b.decode('utf-8')
    for label, pattern in patterns.items():
        if re.search(pattern, b):
            hits.append({'candidate_path': entry['candidate_path'], 'label': label})
assert hits == [], hits
review_note = {
    'reviewer_role': 'owner content qualification; independent review pending root',
    'candidate_content_review': {
        'stage_command_receipt_maps': 'metadata only; exact paths, immutable Git and original SHA; no DB/body/header/session payload',
        'stage_logs': 'all 18 admitted original logs read completely; only pytest summary/static diagnostics/source paths. RED excerpt selected assertion/path/summary lines only, excludes fixture repr',
        'case_receipts': 'two files read completely; static test nodeids, 9 named counters, scope/setup1 only; no runtime IDs/cookies/body',
        'source_copies': 'fixed Git production/test code already authored/read; explicit synthetic fixtures and source strings, no actual secrets',
        'documentary_scripts_reports': 'bounded source/readback/report content; no raw DB/ZIP/runtime/profile/private fixture payload',
    },
    'bounded_scanner_patterns': list(patterns), 'bounded_scanner_hits': hits,
    'limits': 'No blanket safety guarantee or raw runtime admission; exact candidate allowlist only',
}
candidate('CANDIDATE_CONTENT_REVIEW.json', js(review_note), {'type': 'new_owner_content_qualification', 'product_execution': False})
manifest = {'scope': 'Only exact publication-candidates entries plus these two outer metadata files are admitted for independent read',
            'base': BASE, 'final': FINAL, 'candidate_base': str(CANDIDATES),
            'candidate_count': len(entries), 'entries': entries,
            'outer_metadata': ['SAFE_CANDIDATES.json', 'READBACK.json'],
            'excluded': 'All unlisted files, original full pytest RED raw log, runtime/DB/ZIP/profile/secret/temp directories; no recursive read authorization'}
(SEAL / 'SAFE_CANDIDATES.json').write_bytes(js(manifest))
readback = {'scope': 'Owner exact candidate identity/readback, no product rerun or independent approval',
            'final': FINAL, 'candidate_count': len(entries),
            'candidate_total_bytes': sum(e['candidate_size'] for e in entries),
            'manifest_sha256': sha((SEAL / 'SAFE_CANDIDATES.json').read_bytes()),
            'all_candidate_hash_size_exact': True, 'identity_entries': sum(e['transformation'] == 'identity' for e in entries),
            'bounded_excerpt_entries': sum(e['transformation'] != 'identity' for e in entries),
            'source_maps': 7, 'source_bindings': 10686, 'distinct_source_blobs': 1516,
            'stage_maps': 38, 'stage_bindings': map_bindings, 'stage_count': 19,
            'source_final_live_complete_exact': True, 'source_final_clean': True,
            'content_review_sha256': sha((CANDIDATES / 'CANDIDATE_CONTENT_REVIEW.json').read_bytes()),
            'report_sha256': sha((CANDIDATES / 'REPORT.md').read_bytes()),
            'real_cli_model_host_probe': 'NOT_RUN', 'canonical_remote_mutation': 'NONE',
            'root_independent_review': 'separate pending exact seal readback'}
(SEAL / 'READBACK.json').write_bytes(js(readback))
for e in entries:
    raw = (CANDIDATES / e['candidate_path']).read_bytes()
    assert len(raw) == e['candidate_size'] and sha(raw) == e['candidate_sha256']
assert git('rev-parse', 'HEAD').decode().strip() == FINAL and git('status', '--porcelain') == b''
print(json.dumps({'seal': str(SEAL), 'candidates': len(entries),
                  'safe_sha256': sha((SEAL / 'SAFE_CANDIDATES.json').read_bytes()),
                  'readback_sha256': sha((SEAL / 'READBACK.json').read_bytes()),
                  'report_sha256': sha((CANDIDATES / 'REPORT.md').read_bytes()),
                  'final_source': FINAL, 'source_bindings': 10686, 'stage_bindings': map_bindings}))
