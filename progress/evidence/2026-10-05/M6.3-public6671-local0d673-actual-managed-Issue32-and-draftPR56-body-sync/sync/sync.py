import datetime,hashlib,json,subprocess
from pathlib import Path
b=Path('$HOME/.cache/learning-workbench-acceptance');o=Path(__file__).parent
public='6671dd5c924edbac8ca7f479c4f51d4afec14480';local='0d67327f701f3768bc3cc7e084cf0f811f742dc2';source='495e4daddddb64460326659be5af341085654131'
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
assert sha(i['body'].encode())=='d84bf06da107fe422752f4fc0f6473f4914f1586a6f228c4a06aa115bd9da80e'
assert sha(p['body'].encode())=='fc3af879fdb7565b58498a20570f683cac53cac1b1a831e931d2a59bf598c55a'
assert p['head']['sha']==public and p['draft'] and p['state']=='open' and p['merged_at'] is None
snapshot=json.loads((b/'m63-ci-public6671-observation-oct05/51-SNAPSHOT.json').read_text());assert snapshot['source']==public and all(x['status']=='in_progress' for x in snapshot['actual_events'])
shared=f'''M6.3 in_progress，整个M6.3/AC21尚未验收。唯一规范PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec，已批准补充按现行合同实施。

已公开branch与草稿PR56 head为{public}，draft/open/unmerged，依赖PR55。现有实现包括受控turn、逐操作审批、安全控制与只读SSE、产物清单和普通Import待审草稿回导、持久原命令/当前GET分离的会话中断UI。回导后需明确确认、人审和发布。

本地已完成新不可执行准备上下文v4：固定source{source}，正常本地merge8b8699d3aad45180ab3b339ea60979c1478f0b92，文档checkpoint{local}。当前仅本地待发布，保留原用户b895clean和所有旧progress/历史。新v4固定完整已受检BootstrapSnapshot、digest、Provider配置版本、任务材料和历史来源，同事务重核owner原件；严格implemented=false和有序三项缺资格。prepare可保存本地Job，GET纯读；外发preview仍503/CODEX_INPUT_PROOF_UNAVAILABLE，无proposal/consent/start。main/生产registry/executor/HTTPDTO/规范/core/0001未因这个切片改变。

固定495原focused30PASS、related九文件334PASS（log4498de118c8223259e724d6024fd2efd2cd23091ab207bd95bc33de296ac00d5/d293aaf94247e44c99c376792e5dd2ddefd8d3913e3e24eae842e6fe72973fe5）；Ruff全项目/mypy288/gen82/specM0结构/diff均0，七stage1527完整输入前后exact。root源/Spec/Standards独审0P1/P2，并独核116显式候选、19stage38maps58024binding及7Gitmaps10686binding。原REPORT Ruff范围文字偏差由独立勘误说明，原件不改；原pytestRED1FAIL→同83行test GREEN1PASS、原mypy一次FAIL含3diagnostics/RuffF401均保留。18案×9namedseam观察0仅新unavailable阶段，合成bootstrapsetup1和两history各2memorypeer请求另列，非全流程/OS/真实模型保证。Restart仅未进入lifespan的持久读回；legacy手工pair仅codec，不冒充旧Provider授权。

公开6671两次原CI attempt1：push37234694749、pull_request37234699481，实际快照{snapshot['observed_utc']}各5SUCCESS、仅integration IN_PROGRESS。十原完整joblog已取得：两backend各926PASS、frontend各1421PASS/167files、spec各962PASS、browser各133PASS（push29.1m/PR28.9m，首Review22.7s/21.5s在原30s预算内，第二各18.3s），security为固定21841path扫描。两个integration尚无本轮原计数/skip/日志终态，整组未报PASS。failurediagnostic upload步骤SKIPPED，未验收失败上传；四原numericZIP digest/size匹配，6DTO引用合计4逻辑Job记录，实际failed/environment_unavailable/BLOCKED/exit1、发布409/未发布，不当作六次执行或物理进程次数。Restore未列字段不补0，APPROVED合成意图不替代实际数值结果。

新495/8b86后端源已变化，旧4353完整4341PASS/2真实numericENVskip只能保留历史，不能继承新完整Python/native验收；上述新子集与公开6671浏览器成功分源码限定，不相加。旧35ae双原CI各browser132PASS1FAIL及integration2467PASS/2ENVskip、首Review唯一原因UNKNOWN、其他旧失败及首动态raw永久LOSS都保留，后续成功不追改失败。

本地待发布0d673已暂存211文档/显式证据文件diff0/publicationscan0；当前22050路径中21833旧path mode/type/blob沿用已独审6671，217新增/改变路径和待推送226新对象经限定扫描0疑点。没有一般PII/数学来源/物理安全保障的扩大声明；原空白/路径扫描FAIL及具体原件转换保留。

下一内部切片已从8b86隔离启动：固定规范9个nonexperimental schema原bytes/93,287B/97内部ref及具名来源摘要，再加有限strict interrupt形状/decline-cancel响应codec。仅内部不可执行目录，不接HTTP/v4/main/registry；来源是先前离线记录，不重新CLI生成，不把experimental同名三差异替换规范原件。实现/测试未终态前不报成功。

production完整InputProof/profile/checker/完整turn协议/受控executor仍缺实际实现与资格，属于工程缺口。真实DeepSeek/CLI模型turn、工具/物理Broker资源和停止、物理数值、来源数学教学质量、M6.3/AC21/M7未验收；M7仍todo。这个续作0真实外部模型调用，用户key未使用/入库/上传。已中止扩展host probes不重启；没有GitHubmerge/release/deploy/原CI取消或rerun。

下一任务：取得6671两integration真实终态及完整12原log，再按固定源码补实际CI记录；独立审查新catalog有限实现和原RED/GREEN证据，继续production完整输入/执行工程。只在旧原CI结束后发布下一合格源码，保留缺口与失败事实。'''
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
put('READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_head':public,'local_unpublished_head':local,'qualified_source':source,
 'issue_body_sha256':sha(body.encode()),'pr_body_sha256':sha(prbody.encode()),'issue_unmanaged_metadata_unchanged':True,'draft_open_unmerged':True,
 'originalCIsequence':51,'originalCIstatus':'BOTH_INTEGRATION_RUNNING','new_catalog':'IMPLEMENTATION_STARTED_NOT_ACCEPTED','external_models':0,'sourcepush_or_merge_release_deploy':False})
print('Actual Issue32 and draftPR56 bodies updated/readback; local-unpublished source separated from public6671 CI.')
