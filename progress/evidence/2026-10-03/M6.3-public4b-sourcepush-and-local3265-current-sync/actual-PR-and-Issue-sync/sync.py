import datetime,hashlib,json,re,subprocess
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance');O=Path(__file__).parent;H='4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f';REPO='kl3574/Learning_Workbench';sha=lambda b:hashlib.sha256(b).hexdigest()
assert not (O/'pr-before.json').exists()
def invoke(name,command):
 p=subprocess.run(command,capture_output=True);(O/(name+'.stdout')).write_bytes(p.stdout);(O/(name+'.stderr')).write_bytes(p.stderr);(O/(name+'.invocation.json')).write_text(json.dumps({'command':command,'exit_code':p.returncode,'stdout_sha256':sha(p.stdout),'stderr_sha256':sha(p.stderr)},indent=2)+'\n');return p
def read(label,path):
 p=invoke(label,['gh','api','repos/'+REPO+'/'+path]);assert p.returncode==0;(O/(label+'.json')).write_bytes(p.stdout);return json.loads(p.stdout)
pr=read('pr-before','pulls/56');issue=read('issue-before','issues/32')
assert pr['head']['sha']==H and pr['draft'] and pr['merged_at'] is None and pr['state']=='open'
assert sha(pr['body'].encode())=='aba2efa94c6202747c186a746eb63a8ae9f876efc3c38a56fe0c5dcde2554aaa'
assert issue['state']=='open' and sha(issue['body'].encode())=='0edbd8d94d28b1ac8d4ad099a6d36f7c0bf6cd2fb17f177a6cbf61bbca47f258'
body=(B/'m63-source-publication-4b5516bd-oct04/pr-body.md').read_text();title='M6.3: 受控回合准备、单次许可与调度'
(O/'pr-body.md').write_text(body);(O/'pr-patch.json').write_text(json.dumps({'title':title,'body':body},ensure_ascii=False))
p=invoke('pr-patch',['gh','api','repos/'+REPO+'/pulls/56','--method','PATCH','--input',str(O/'pr-patch.json')]);assert p.returncode==0
pattern=r'<!-- engineering_progress:start -->.*?<!-- engineering_progress:end -->';blocks=re.findall(pattern,issue['body'],re.S);assert len(blocks)==1;block=blocks[0]
old='公开源码仍69029bc1ab355efdbb6e0fdb8a86204c59cea71a，PR56 draft/open/unmerged、依赖PR55/e287。该固定源码push37170415116与PR37170416801各六job实际SUCCESS；'
new='公开最新源码4b5516bd2a78d7b39f9b4a4c321a6d91ad4ca78f已实际普通push，branch与PR56新headfresh读回一致；首次PRhead仍旧690的读回FAIL保留，没有重复push。PR56 draft/open/unmerged、依赖PR55/e287。4b相对受测29e仅终态progress，1433工程输入一致。新CI尚未读回终态，不能借旧CI声称成功。此前690固定源码push37170415116与PR37170416801各六job实际SUCCESS；'
assert old in block;block=block.replace(old,new)
block=block.replace('1433完整非progress Git输入，127实际/147声明/20尚未注册，仍未推送。','1433完整非progress Git输入，127实际/147声明/20尚未注册，4b文档检查点已推送。')
block=block.replace('完整Python runner期间源码/GitHEAD保持冻结；实际终态后才解除冻结，准备收录终态并正常push。','完整Python runner期间源码/GitHEAD保持冻结；实际终态后才解除冻结，三个明确候选终态package/进度已提交4b，spec/publication/diffcheck通过并核当前19475文件/1314outgoingobjects/812blobs后普通push。')
block=block.replace('尚未合canonical/不称实际工具。生产registry仍空，','尚未合canonical/不称实际工具。独立静态新P2：profile未冻结实际prepare/execute包装路径，root原无finding追加更正，9d209PASS不覆盖此遗漏；保留原封包并先RED后窄修。生产registry仍空，')
block=block.replace('组件/hooks完整门禁待完成，不称旧b149产品缺陷。','固定43c6完整Web1272/157files与strict/build/spec/214ownerPASS；新合法保留回答却failed/cancelled与URL规范化反例5FAIL/30PASS已保留，修复92c8836相关73PASS/strict0，最新完整门禁RUNNING；旧complete_failed过强oracle明确纠正、不称整文件同字节反转，尚未合canonical。')
block=block.replace('将实际29e完整Python4085PASS/2真实数值ENVskip、1201Web/staticPASS及native130PASS（原wrapperFAIL单独保留）的明确候选收录进度，普通push并读回PR56与实际新CI；','核本次4b实际新CI终态；继续修新memory运行闭包P2和outbound结果关系、独立复核与正常本地整合受检owner；')
block=block.replace('没有上传密钥、GitHubmerge/release/deploy或新sourcepush。','本次唯一普通sourcepush4b已验证，密钥未上传；没有GitHubmerge/release/deploy或实际模型请求。')
bodyissue=re.sub(pattern,lambda _:block,issue['body'],flags=re.S);(O/'issue-body.md').write_text(bodyissue);(O/'issue-patch.json').write_text(json.dumps({'body':bodyissue},ensure_ascii=False))
p=invoke('issue-patch',['gh','api','repos/'+REPO+'/issues/32','--method','PATCH','--input',str(O/'issue-patch.json')]);assert p.returncode==0
pa=read('pr-after','pulls/56');ia=read('issue-after','issues/32')
assert pa['title']==title and pa['body']==body and pa['head']['sha']==H and pa['draft'] and pa['merged_at'] is None
assert ia['body']==bodyissue and re.sub(pattern,'',ia['body'],flags=re.S)==re.sub(pattern,'',issue['body'],flags=re.S)
for field in ['state','labels','assignees','milestone']:assert pr[field]==pa[field] and issue[field]==ia[field]
assert issue['title']==ia['title'] and pa['base']['ref']==pr['base']['ref']
r={'status':'PUBLISHED_4B_PR56_DESCRIPTION_AND_ISSUE32_CURRENT_STATE_SYNC_VERIFIED','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':H,'tested_runtime_source':'29e864a6157f3bb23c6ced5d1a2f34f77bf3b875','pr56_draft':pa['draft'],'pr56_state':pa['state'],'pr56_merged_at':pa['merged_at'],'pr56_body_sha256':sha(body.encode()),'issue32_body_sha256':sha(bodyissue.encode()),'outside_issue_block_and_metadata_unchanged':True,'sourcepush_by_this_sync':False,'boundary':'Actual title/body-only PR and managedblock-onlyIssue sync after separatelyverified normal4b sourcepush. New CI not yetterminal, root29e scopedfullPASS only; numericENVblocked/realprovider0/wholeM6.3 unaccepted. Isolated9dclosureP2 andUI92gatespending; noGitHubmerge/release/deploy.'};(O/'readback.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
