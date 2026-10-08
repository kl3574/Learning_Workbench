import datetime,hashlib,json,subprocess
from pathlib import Path
b=Path('$HOME/.cache/learning-workbench-acceptance');o=Path(__file__).parent
public='1e7ad7a8656c0dc8373d4181fa3002f385ed1847';local=public;source='27f549ff5a8fd67b0a601b67a5ba51ef35f6765f'
def sha(x):return hashlib.sha256(x).hexdigest()
def put(name,x):(o/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def gh(name,*args):
 assert not (o/(name+'-command.json')).exists()
 put(name+'-command.json',{'argv':['gh',*args],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(['gh',*args],capture_output=True);(o/(name+'.stdout')).write_bytes(x.stdout);(o/(name+'.stderr')).write_bytes(x.stderr)
 put(name+'-receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(name,x.returncode)
 return json.loads(x.stdout)
assert gh('identity','api','user')['login']=='kl3574'
i=gh('issue-before','api','repos/kl3574/Learning_Workbench/issues/32');p=gh('pr-before','api','repos/kl3574/Learning_Workbench/pulls/56')
assert sha(i['body'].encode())=='6e3d8245fa459427d1482eb36e80c746eead5b2624aca03d2c1c597e6eb53aca'
assert sha(p['body'].encode())=='225e834e206f60cd4df109081da10aad465b120d68ea2482814d3ca94ea82f39'
assert p['head']['sha']==public and p['draft'] and p['state']=='open' and p['merged_at'] is None
snapshot=json.loads((b/'m63-ci-public1e7ad-observation-oct05/01-SNAPSHOT.json').read_text());assert snapshot['source']==public and len(snapshot['actual_events'])==2 and all(x['run_attempt']==1 for x in snapshot['actual_events'])
shared=f'''M6.3 in_progress，整个M6.3/AC21尚未验收。唯一规范PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec，已批准的受控turn补充按现行合同实施。

已公开branch与草稿PR56 head为{public}，实际2026-10-04T22:44:26.904920UTC读回同head，draft/open/unmerged，依赖PR55。此次普通sourcepush包含已独核准备闭包v4与离线schema目录/有限codec、明确测试证据和进度。未GitHubmerge/release/deploy。

准备闭包v4固定source495e4daddddb64460326659be5af341085654131：同SQLite事务冻结和重核已检查BootstrapSnapshot/digest/Provider配置/任务材料与历史；implemented严格false，明确production_input_proof_unregistered、production_turn_protocol_unregistered、production_turn_runtime_unregistered。prepare仅建真实本地Job和原件，GET纯读，外发preview仍503/CODEX_INPUT_PROOF_UNAVAILABLE，无proposal/consent/start。原focused30/related九文件334和5static实际通过；root独核116明确候选，原RED/mypy3diagnostics/RuffF401及独立范围勘误保留。

新离线目录source{source}，正常localmerge8978880982f4190ce688d7fbf2a9be72d30d5657：严格校验规范指定9原schema/93287bytes/97localrefs，固定非秘密历史来源摘要2101bytes；私有完整receipt55893未入Git。codec仅序列化interrupt params或decline/cancel响应，不构成完整RPC、owned mapping、审批/发送/执行权限。生产main/ProofRegistry/executor仍空/None，原HTTP/54core/0001未改。固定27f原68focused/186related三文件/5static真实PASS；186含v4的30，不与旧334相加。Ruff全项目0/mypy290files0/gen82/specM0结构/diff0；root独核98候选、1541当前源、7Gitmaps10760bindings、15阶段46204bindings，Spec/Standards0P1P2。原first1FAIL→同27行1PASS、typed1FAIL65PASS→同239行66PASS、RuffF401/mypy调用exit2保留；没有真实CLI/model。

原公开6671 attempt1 push37234694749/PR37234699481现已各6job SUCCESS（terminal57 at22:20:03UTC）。每组backend926PASS、frontend1421PASS167files、spec962PASS、browser133PASS、integration2467PASS/2真实numericENVskip/2warnings；pushintegration4354.97s、PR4297.49s。owner12完整原joblog已核，root此前读4browser/integration原log；另一peer独验88候选1384checks，未打开私有完整log/ZIP。push6671/PRab37同treefe6a9cf，CI working-input before/aftermaps NOT_CAPTURED。原数值仍failed/environment_unavailable/BLOCKED/exit1，发布409未发布；6DTO=4logicalJob不是processcount，缺字段保留ABSENT。failurediagnostic步骤14均SKIPPED，失败上传资格NOT_RUN。旧35ae双FAIL、原因UNKNOWN及永久原rawLOSS全部保留。

新公开1e7ad两原CI实际已创建：push37241154917、PR37241158099，attempt1，最新已保存快照{snapshot['observed_utc']}；当时push queued/PR in_progress，各job queued/in_progress，未有新终态PASS。不借旧6671CI验收新495/27f后端。已启动27f完整Python原命令uv run --frozen --offline pytest，collected4441，session81265；截至本次记录尚无终态。其contract/test_tutor_transport进度出现真实F，详情待原完整日志；另行同source定向实测该SSE TypeScript执行case实际1FAIL：Node24.21.0 required/setup缺失，1541beforeafterexact（logbc4c83b8d6b7f54c3705ef615d291981455896af936331d5fb2c4cabe892cf2d）。这只确认独立定向失败的准备原因，不追认原完整suite唯一根因，不称已修复。原完整命令继续不改环境，另隔离tree按现有锁定setup准备后重验。新wholePython/native尚未验收。

本次固定待推送1e7ad审查：22290当前路径，其中21833旧mode/type/blob沿固定6671已独审来源保持；457新增/变化路径及514待推送新对象有限扫描0疑点。8明确证据包433newfiles+4docs，HOME/runnerprefix转换明确；私有原receipt、DB、完整CIlog/ZIP等未准入Git。扫描只是限定补充，不作全面PII/物理安全/学术质量保证。原用户b895clean保持。

production完整InputProof、完整turn协议与受控runtime仍缺实现及真实资格，属于工程缺口。真实DeepSeek/CLI模型turn、工具/Broker资源与停止、物理数值、来源数学教学、整个M6.3/AC21/M7未验收；M7仍todo。本续作0外部模型请求，用户key未使用/入库/上传；不重启已拒绝host probes，无原CI取消或rerun。

下一任务：保留并取得新原完整Python和新公开CI终态/原日志；在新隔离tree补锁定Node准备并对失败原case重验；继续规范范围内内部RPC/response/terminal pairing实现，生产仍unregistered/unavailable。真实完整输入和单次外发执行资格另行落实，不能以codec或subset替代真实Agent验收。'''
begin,end='<!-- engineering_progress:start -->','<!-- engineering_progress:end -->';assert i['body'].count(begin)==i['body'].count(end)==1
prefix=i['body'].split(begin)[0];suffix=i['body'].split(end)[1];body=prefix+begin+'\n'+shared+'\n'+end+suffix
put('issue-patch.json',{'body':body});(o/'issue-body.md').write_text(body)
gh('issue-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/issues/32','--input',str(o/'issue-patch.json'))
ia=gh('issue-after','api','repos/kl3574/Learning_Workbench/issues/32');assert ia['body']==body
assert {k:i[k] for k in ['number','title','state','labels','milestone','assignees']}=={k:ia[k] for k in ['number','title','state','labels','milestone','assignees']}
assert ia['body'].split(begin)[0]==prefix and ia['body'].split(end)[1]==suffix
prbody='本PR实现现行v3.0.15受控回合、逐操作审批、只读控制事件和受检产物回导。产物通过普通Import进入待审草稿，再经明确确认、人审和发布。会话中断保持原actor/CAS/body/key，当前状态与历史ACK分开。\n\n'+shared+'\n\nRefs #32\n'
put('pr-patch.json',{'body':prbody});(o/'pr-body.md').write_text(prbody)
gh('pr-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/pulls/56','--input',str(o/'pr-patch.json'))
pa=gh('pr-after','api','repos/kl3574/Learning_Workbench/pulls/56');assert pa['body']==prbody and pa['head']['sha']==public and pa['draft'] and pa['state']=='open' and pa['merged_at'] is None and pa['title']==p['title'] and pa['base']['sha']==p['base']['sha']
put('READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_head':public,'published_head':public,'qualified_source':source,
 'issue_body_sha256':sha(body.encode()),'pr_body_sha256':sha(prbody.encode()),'issue_unmanaged_metadata_unchanged':True,'draft_open_unmerged':True,
 'originalCIsequence':1,'originalCIstatus':'NEW_PUBLIC1E_EVENTS_QUEUED_OR_RUNNING','old6671':'TWO_TERMINAL_SUCCESS_SEPARATE','new_catalog':'SCOPED_GATES_ROOT_QUALIFIED_PUBLISHED','new_full_python':'RUNNING_OBSERVED_F_NOT_TERMINAL','focused_original_failure':'NODE24_21_SETUP_REQUIRED_NOT_REPAIRED','external_models':0,'sourcepush_or_merge_release_deploy':False})
print('Actual Issue32 and draftPR56 bodies updated/readback; published1e scoped slice/current running gates and old6671 terminal qualified separately.')
