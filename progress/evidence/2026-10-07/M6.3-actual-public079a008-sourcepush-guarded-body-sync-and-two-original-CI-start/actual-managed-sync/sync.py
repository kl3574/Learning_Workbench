from pathlib import Path
import datetime,hashlib,json,subprocess
O=Path(__file__).resolve().parent;B=O.parent;PUBLIC='079a008cf88b37e4517cb391503a1e7393ccf374';SOURCE='d78c4d159a2831f7d5e1721a9a466ec5b3e66421'
def sha(b):return hashlib.sha256(b).hexdigest()
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def gh(n,*args):
 assert not (O/(n+'-command.json')).exists();put(n+'-command.json',{'argv':['gh',*args],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x=subprocess.run(['gh',*args],capture_output=True);(O/(n+'.stdout')).write_bytes(x.stdout);(O/(n+'.stderr')).write_bytes(x.stderr)
 put(n+'-receipt.json',{'exit_code':x.returncode,'stdout_sha256':sha(x.stdout),'stderr_sha256':sha(x.stderr),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert x.returncode==0,(n,x.returncode);return json.loads(x.stdout)
push=json.loads((B/'m63-d78-documentary-publication-oct07/READBACK.json').read_bytes());assert push['expected_head']==PUBLIC and push['branch_head']==push['pr_head']==PUBLIC and push['git_exit_code']==0
assert gh('identity','api','user')['login']=='kl3574'
i=gh('issue-before','api','repos/kl3574/Learning_Workbench/issues/32');p=gh('pr-before','api','repos/kl3574/Learning_Workbench/pulls/56')
assert sha(i['body'].encode())=='77fb50ac69ac6fd19e7f05b3e08cf85146dea169fef157f6db9ded800ec29d6d'
assert sha(p['body'].encode())=='8d518336200def21a099f23299fcb8e96f87cd3fd334f48068aece5b6692de7e'
assert p['head']['sha']==PUBLIC and p['draft'] and p['state']=='open' and p['merged_at'] is None
q=max((B/'m63-ci-public079a008-observation-oct07').glob('*-SNAPSHOT.json'),key=lambda x:int(x.name.split('-')[0]));snapshot=json.loads(q.read_bytes())
assert snapshot['source']==PUBLIC and {e['id'] for e in snapshot['actual_events']}=={37632652743,37632662238}
rows=[]
for e in snapshot['actual_events']:
 assert e['run_attempt']==1
 counts={}
 for j in e['jobs']:
  k=j['conclusion'] or j['status'];counts[k]=counts.get(k,0)+1
 rows.append(f"- [{e['event']} {e['id']}]({e['html_url']})：{e['status']} / {e['conclusion'] or '尚无终态'}；jobs {json.dumps(counts,ensure_ascii=False)}")
shared=f'''M6.3 in_progress；整个 M6.3 / AC-21 尚未验收，M7 保持 todo。唯一规范 PRODUCT_DESIGN.md v3.0.15，SHA b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec。

公开分支和草稿 PR56 已实际回读 `{PUBLIC}`（2026-10-07T13:57:14.574769UTC），1561 工程输入；运行源码锚点 `{SOURCE}`，之后仅进度证据与三个确切归档 whitespace 规则。原用户 b895 检出仍干净未改；本次为普通源码 push，没有 GitHub merge、release 或部署。

实际实现及有限验收：

- 私有 interrupt RPC 的严格配对、递归异常拒绝已实现：固定68a原120专项、290相关六文件、5静态通过；同502行原RED2FAIL与修复后GREEN120PASS均保留。
- Broker6f将两个取消入口通过具名owner绑定当前受检回调、线程、租约与持久可能发送事实；前向0036和私有v7历史相互核验。实际22专项、473相关十文件、5静态通过，原失败和源码/原阶段独立核验。仅 synthetic_peer_only、生产资格false及显式callback泵送；没有默认生产IPC或自动后台执行。
- Authoring3d只对确证已退出非零UI且所选端口冲突重试一次，共享原20秒期限；需要本ownedVite标记和HTTP，不扫描/停止未知listener。10个ownedNode行为和最终严格TS/build/5browser通过属于不同局部。原TS/list/Chrome长socket路径失败保留；最后同源仅短TMPDIR修正后5PASS，不宣称实际Vite碰撞注入或旧CI根因已闭合。

完整门禁与原失败分开：固定较早68a的原完整Python4561 collected，4559PASS、2真实数值环境SKIP、3warnings，3043.52s；1553全部输入前后一致。它不覆盖后续1561变更。更早27f原完整4433PASS/6FAIL/2SKIP仍为FAIL。旧公开1e两原CI各browser131PASS/2FAIL；原Review/评分失败原因仍UNKNOWN。单独未改1e原grading三个用例3PASS/40.8s、原firstReview唯一一次1PASS/16.4s，均1541全部输入一致；不替代旧FAIL，也未实施产品修复。评分测试202→0丢真实Job状态、Review fixture/page.request/JSONReact/exactURLpoll缺观测均如实保留。

新源码的实际原CI attempt1，快照seq{snapshot['sequence']}，{snapshot['observed_utc']}：

'''+'\n'.join(rows)+'''

以上快照仅反映该时点，不预填用例计数或整组PASS；后续只读观察同两个原事件，不重跑或取消。捕获日志exit0不等于测试成功，CI工作输入before/after未捕获时明确NOT_CAPTURED；原数值BLOCKED没有fallback，产物上传不构成已发布。

发布前实际检查458条进度/证据/归档规则、当前894变更路径与993待推对象，有限扫描0疑点；22281旧路径mode/type/blob连续性保持。原尾空格检查exit2及提交前guard错误保留；三个确切原件归档规则不裁剪测试证据、不放宽秘密扫描。私人API/raw失败载荷、ZIP/PNG/DB/profile及用户密钥未上传。

真实Agent剩余工程：默认空ProofRegistry与executor=None。完整最终模型请求字节的可信producer/checker、单次受限外发、真实App Server完整协议与受限runtime/停止回执仍缺实现/资格；现有schema、bootstrap和synthetic测试不能填补。当前0实际外部模型调用；这是工程缺口，不能把API key或旧CI当成功证明。物理数值BLOCKED、数学来源与教学验收NOT_RUN。备份保留历史而认证/许可不可执行的规范内本地工作继续核验，不能据此解锁M7。

下一任务：取得这两个新原CI的实际完整终态/原日志并处理可复现失败；继续完成规范内真实实现和可靠备份/恢复读回，保留所有旧FAIL/UNKNOWN/LOSS/环境阻塞。生产无完整证明时继续零外发，不重启曾被自动审批拒绝的主机探针。
'''
begin,end='<!-- engineering_progress:start -->','<!-- engineering_progress:end -->';assert i['body'].count(begin)==i['body'].count(end)==1
prefix=i['body'].split(begin)[0];suffix=i['body'].split(end)[1];body=prefix+begin+'\n'+shared+'\n'+end+suffix
put('issue-patch.json',{'body':body});(O/'issue-body.md').write_text(body)
gh('issue-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/issues/32','--input',str(O/'issue-patch.json'));ia=gh('issue-after','api','repos/kl3574/Learning_Workbench/issues/32')
assert ia['body']==body and {k:i[k] for k in ['number','title','state','labels','milestone','assignees']}=={k:ia[k] for k in ['number','title','state','labels','milestone','assignees']}
assert ia['body'].split(begin)[0]==prefix and ia['body'].split(end)[1]==suffix
prbody='受控回合、逐操作审批与产物回导保持明确人审边界；本次补上严格interrupt RPC、持久Broker合成控制以及Authoring owned启动修复和实际失败证据。生产Agent尚未验收，产物只回导待审草稿。\n\n'+shared+'\n\nRefs #32\n'
put('pr-patch.json',{'body':prbody});(O/'pr-body.md').write_text(prbody)
gh('pr-write','api','--method','PATCH','repos/kl3574/Learning_Workbench/pulls/56','--input',str(O/'pr-patch.json'));pa=gh('pr-after','api','repos/kl3574/Learning_Workbench/pulls/56')
assert pa['body']==prbody and pa['head']['sha']==PUBLIC and pa['draft'] and pa['state']=='open' and pa['merged_at'] is None and pa['title']==p['title'] and pa['base']['sha']==p['base']['sha']
put('READBACK.json',{'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_head':PUBLIC,'runtime_source':SOURCE,'issue_body_sha256':sha(body.encode()),'pr_body_sha256':sha(prbody.encode()),
 'issue_unmanaged_metadata_preserved':True,'draft_open_unmerged':True,'snapshot_sequence':snapshot['sequence'],'snapshot_sha256':sha(q.read_bytes()),'original_events':rows,
 'current_complete_CI':'ORIGINAL_EVENTS_IN_PROGRESS_UNLESS_SNAPSHOT_TERMINAL','model_calls':0,'merge_release_deploy':False})
print('Actual Issue32 managed region and draftPR56 body updated and exactreadback; currentCI only observed snapshot, no fullacceptance claim.')
