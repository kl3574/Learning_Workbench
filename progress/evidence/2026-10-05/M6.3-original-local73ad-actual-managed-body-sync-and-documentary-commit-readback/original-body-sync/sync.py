from pathlib import Path
import datetime,hashlib,json,subprocess
O=Path(__file__).resolve().parent;B=O.parent
PUBLIC='1e7ad7a8656c0dc8373d4181fa3002f385ed1847';LOCAL='73ad831d5a1617e1ad478fb5371c1ae04b27c299';SOURCE='68a280b9cf251bbf79c2ca188ac8b4aefe7562e0'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def gh(n,*args):
 assert not (O/(n+'-command.json')).exists();put(n+'-command.json',{'argv':['gh',*args],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(['gh',*args],capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'exit_code':x.returncode,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr)})
 assert x.returncode==0,(n,x.returncode);return json.loads(x.stdout)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=B/'m62-public-safe-oct02').decode().strip()==LOCAL
assert gh('identity','api','user')['login']=='kl3574'
i=gh('issue-before','api','repos/kl3574/Learning_Workbench/issues/32');p=gh('pr-before','api','repos/kl3574/Learning_Workbench/pulls/56')
assert sha(i['body'].encode())=='edf2e7b9649102411c8e6f8069bf7592fc2d339a8d31816fe1cc0de2698bcf2c'
assert sha(p['body'].encode())=='b9b9875593a6a82784aa369e5365b94d8e054f7c3f5049ad948a7e2431ce1a7d'
assert p['head']['sha']==PUBLIC and p['draft'] and p['state']=='open' and p['merged_at'] is None
q=sorted((B/'m63-ci-public1e7ad-observation-oct05').glob('*-SNAPSHOT.json'))[-1];snapshot=json.loads(q.read_bytes());assert snapshot['source']==PUBLIC and {x['id'] for x in snapshot['actual_events']}=={37241154917,37241158099} and all(x['run_attempt']==1 for x in snapshot['actual_events'])
rows=[]
for e in snapshot['actual_events']:
 counts={}
 for j in e['jobs']:
  k=j['conclusion'] or j['status'];counts[k]=counts.get(k,0)+1
 rows.append(f"{e['event']} {e['id']}：{e['status']}/{e['conclusion'] or '无终态'}，jobs {json.dumps(counts,ensure_ascii=False)}")
shared=f'''M6.3 in_progress；整个M6.3/AC21未验收，M7仍todo。唯一规范 PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec。

公开分支/草稿PR56仍为 `{PUBLIC}`。新的本地检查点 `{LOCAL}`（工程候选 `{SOURCE}`、本地正常合并8e1ad259）已保存，尚未推送；原用户b895检出保持干净未改，无GitHub merge/release/deploy。

本地已实现严格私有interrupt RPC/空控制回复/终态通知配对及有限拒绝记录。空回复不能证明进程停止或副作用撤销。原f81递归缺陷用同502行测试实际2FAIL118PASS，68a一行异常拒绝修复后同测试120PASS；290相关六文件及五静态检查也通过，计数重叠不相加。1553完整工程输入每阶段前后相同；root独核159候选、14 Git图、27原阶段，最终Spec/Standards无新增P1/P2。原失败及报告前缀更正均保留。

原27f完整Python是FAIL：4441 collected，4433PASS/6FAIL/2SKIP/3warnings，1541完整输入前后相同。六个合同用例原stderr均要求Node24.21.0；两个数值skip真实BLOCKED_ENVIRONMENT，没有计算成功或fallback。另一锁定27f环境的定向1PASS/相关21PASS只作局部证据，不覆盖原失败。新68a在按现有make setup锁定依赖的独立树已启动完整pytest，collected4561，尚无终态/after/receipt，不能报完整通过。

公开1e原CI attempt1最新已存快照 seq{snapshot['sequence']}，{snapshot['observed_utc']}：
'''+'\n'.join(rows)+'''

两原browser各131PASS/2FAIL：PR创作服务启动前Vite端口40581被占用，Review在URL reader参数轮询处超时；push评分revision3vs0及Review窄屏步骤contextclosed超时。三个案例、四次失败，原30秒预算/retry0不改，未认定同一产品根因。每组backend994PASS/3warnings、frontend1421PASS/167files、spec962PASS/2warnings、publication扫描22290通过；已结束的PR integration原日志2497PASS/2真实numericENVskip/2warnings。组间不相加，捕获日志exit0不是测试通过。

两个原failure-only产物上传实际SUCCESS；本次6个原ZIP大小/SHA与GitHub吻合且所有成员字节核验。两Review原timing metadata分别36phases/349HTTP和30/284，零dropped；其body计时不含fixture/setup，最后步骤不能证明唯一根因。4个逻辑numeric Job实际failed/environment_unavailable/BLOCKED/exit1，发布409，未发布/refnull；批准意图不能升级为数学通过。ZIP、PNG/error-context及用户载荷保持私有。原push checkout1e、PR checkout88da38fc实际Git tree24ff983950b3798af7be5d8af091587bf8f4d4e7相同，CI工作输入before/after仍NOT_CAPTURED。旧6671各133browser成功只属旧源码，旧35ae失败、UNKNOWN与永久原rawLOSS保留。

本地416文件进度/有限证据提交通过差异检查及发布扫描。原首次398文件扫描因新进度命令cwd个人前缀失败，保留原件，仅替换一处公开HOME前缀后新检查通过，没有放宽scanner。

下一工程正在独立分支实施：具名Broker停止控制owner、append-only私有事实/跨owner v7关联；仅已确认端口碰撞的owned测试服务启动处理。两候选尚未采用，不能提前宣称这些失败已修复。生产完整InputProof/turn协议/受控runtime仍缺资格、Registry/executor保持空/None。真实Provider/Codex模型turn、物理工具/Broker资源/数值、来源数学教学均NOT_RUN或明确BLOCKED。本续作0外部模型调用，密钥未使用或上传；不重启被拒绝host probes。

下一任务：取得新4561完整Python及原1e剩余CI终态，保留所有原失败和真实skip；独立审阅并验收Broker与owned启动修复后再采用，继续唯一规范实施，不借子集或旧源码CI验收完整Agent。
'''
begin,end='<!-- engineering_progress:start -->','<!-- engineering_progress:end -->';assert i['body'].count(begin)==i['body'].count(end)==1
prefix=i['body'].split(begin)[0];suffix=i['body'].split(end)[1];body=prefix+begin+'\n'+shared+'\n'+end+suffix
put('issue-patch.json',{'body':body});(O/'issue-body.md').write_text(body)
gh('issue-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/issues/32','--input',str(O/'issue-patch.json'));ia=gh('issue-after','api','repos/kl3574/Learning_Workbench/issues/32')
assert ia['body']==body and {k:i[k] for k in ['number','title','state','labels','milestone','assignees']}=={k:ia[k] for k in ['number','title','state','labels','milestone','assignees']}
assert ia['body'].split(begin)[0]==prefix and ia['body'].split(end)[1]==suffix
prbody='受控turn实现保持默认能力关闭；当前补上本地RPC配对、递归拒绝修复及原失败可核记录，真实生产Agent尚未验收。产物仍只回导待审草稿，经明确确认和人审发布。\n\n'+shared+'\n\nRefs #32\n'
put('pr-patch.json',{'body':prbody});(O/'pr-body.md').write_text(prbody)
gh('pr-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/pulls/56','--input',str(O/'pr-patch.json'));pa=gh('pr-after','api','repos/kl3574/Learning_Workbench/pulls/56')
assert pa['body']==prbody and pa['head']['sha']==PUBLIC and pa['draft'] and pa['state']=='open' and pa['merged_at'] is None and pa['title']==p['title'] and pa['base']['sha']==p['base']['sha']
put('READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_head':PUBLIC,'local_unpushed_head':LOCAL,'source':SOURCE,'issue_body_sha256':sha(body.encode()),'pr_body_sha256':sha(prbody.encode()),'issue_unmanaged_metadata_unchanged':True,'draft_open_unmerged':True,'snapshot_sequence':snapshot['sequence'],'snapshot_sha256':sha(q.read_bytes()),'original_public_CI':rows,'older27f_full':'ACTUAL6FAIL4433PASS2ENVSKIP3WARN','new68a_full':'RUNNING4561_NOT_TERMINAL','actual_models':0,'sourcepush_merge_release_deploy':False})
print('Actual guarded Issue32/PR56 bodies updated and exactreadback; public1e separate from local73ad/unpushed68a, original failures retained.')
