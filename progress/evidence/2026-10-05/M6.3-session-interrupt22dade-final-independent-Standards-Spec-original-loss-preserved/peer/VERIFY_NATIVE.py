"""Verify explicit native candidates against fixed Git input map; no product run."""
from pathlib import Path
import json,hashlib,subprocess
here=Path(__file__).parent
repo=Path('$HOME/.cache/learning-workbench-acceptance/m63-session-interrupt-ui-oct05')
p=Path('$HOME/.cache/learning-workbench-acceptance/m63-session-interrupt-native-22dade-oct05/seal-22dade')
b=p/'publication-candidates';h='22dade7996f13634202250ef5e1c05dc976214a5'
sha=lambda v:hashlib.sha256(v).hexdigest()
mr=(p/'SAFE_CANDIDATES.json').read_bytes();orr=(p/'READBACK.json').read_bytes()
assert sha(mr)=='4456e4fab0ba7766964daa64cb70123e49779d4a23116792e6b2468dc22e7dfc'
assert sha(orr)=='cdc3573672865b0a1eab7866a642775447d9ee6201e91dfe5784912551fb2b33'
m=json.loads(mr);assert m['source']==h and len(m['files'])==38
entries={};payloads={}
for e in m['files']:
 n=e['candidate_path'];assert not Path(n).is_absolute() and '..' not in Path(n).parts and n not in entries
 v=(b/n).read_bytes();assert len(v)==e['bytes'] and sha(v)==e['sha256'] and e['transformation']=='none'
 entries[n]=e;payloads[n]=v
ref={};oids=set()
for line in subprocess.check_output(['git','ls-tree','-rz',h],cwd=repo).split(b'\0'):
 if not line:continue
 meta,path=line.split(b'\t',1);mode,kind,oid=meta.decode().split();path=path.decode()
 if path.startswith('progress/'):continue
 assert kind=='blob';ref[path]=dict(mode=mode,type=kind,git_blob=oid);oids.add(oid)
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=repo,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
v,_=proc.communicate(('\n'.join(sorted(oids))+'\n').encode());assert proc.returncode==0
at=0;blob={}
for oid in sorted(oids):
 end=v.index(b'\n',at);actual,kind,size=v[at:end].decode().split();size=int(size);data=v[end+1:end+1+size];at=end+size+2
 assert actual==oid and kind=='blob' and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+data).hexdigest()==oid
 blob[oid]=dict(bytes=size,sha256=sha(data))
assert at==len(v)
for item in ref.values():item.update(blob[item['git_blob']])
assert len(ref)==1525
maps=[n for n in entries if n.endswith(('before.json','after.json','terminal-source.json'))]
assert len(maps)==9
for n in maps:
 obj=json.loads(payloads[n]);assert obj['head']==h and obj['count']==len(obj['files'])==1525 and set(obj['files'])==set(ref)
 for path,v in obj['files'].items():assert all(v[k]==ref[path][k] for k in ['mode','type','git_blob','bytes','sha256'])
assert all(json.loads(payloads[n])==json.loads(payloads[maps[0]]) for n in maps)
runs=[]
for n in ['run-01','run-02']:
 cmd=json.loads(payloads[n+'/command.json']);rec=json.loads(payloads[n+'/run-receipt.json'])
 assert rec['source_sha']==h and {k:rec[k] for k in cmd}==cmd
 for name,digest in rec['harness'].items():assert sha(payloads[n+'/'+name])==digest
 for step in rec['steps']:
  label='build' if 'vite.js' in step['command'][1] else 'native'
  assert sha(payloads[n+'/'+label+'.log'])==step['log_sha256']
 runs.append(dict(run=n,exit_code=rec['exit_code'],started_at=rec['started_at'],finished_at=rec['finished_at'],steps=rec['steps'],harness=rec['harness']))
assert runs[0]['exit_code']==1 and runs[1]['exit_code']==0
loss=json.loads(payloads['LOSS_V2.json']);lost=json.loads(payloads['FIRST_RUN_PRESERVATION_LOSS.json'])
assert loss['first_attempt']['dynamic_files_retained'] is False and loss['first_attempt']['product_verification']=='NOT_RUN'
assert loss['accidental_second_attempt_in_run01']==json.loads(payloads['run-01/run-receipt.json'])
assert loss['first_attempt']['native_log_sha256_from_original_tool_output']==lost['original_first_native_log_sha256']
assert loss['first_attempt']['build_log_sha256_from_original_tool_output']==lost['original_first_build_log_sha256']
assert all(sha(payloads['run-01/'+n])==v for n,v in loss['same_original_script_hashes'].items())
runner=payloads['run-02/run.py'].decode();assert "('command.json', 'run-receipt.json', 'native.log', 'build.log')" in runner
assert "'failure.json'" not in runner and "'receipt.json'" not in runner
receipt=json.loads(payloads['run-02/receipt.json']);terminal=json.loads(payloads['run-02/terminal-sentinels.json'])
assert receipt['source']==h and receipt['status']=='CONTROLLED_SESSION_INTERRUPT_UI_NATIVE_PASS'
assert receipt['browser_ui_interrupt_requests']==4 and receipt['separate_fixture_competing_interrupt_requests']==1
assert receipt['actual_CLI']==receipt['actual_remote_model']==receipt['actual_tool_process']=='NOT_RUN'
assert terminal['counts']==receipt['sentinels']['counts']==dict(codex_executor=0,provider_transport=0,literal_operation=0,later_bootstrap=0)
assert terminal['phase']=='lifespan-exited' and receipt['sentinels']['phase']=='lifespan-entered'
assert terminal['executor_none'] and terminal['synthetic_bootstrap_calls']==1
png=[]
for e in receipt['screenshots']:
 n='run-02/'+e['file'];assert sha(payloads[n])==e['sha256'];assert payloads[n].startswith(b'\x89PNG\r\n\x1a\n')
 g=e['geometry'];assert g['scroll']<=g['client']+1 and g['document']<=g['viewport']
 png.append(dict(candidate=n,bytes=len(payloads[n]),sha256=sha(payloads[n]),geometry=g,independently_viewed=True,qualification='Original screenshot, viewport slice only; no whole-page/late-body/physical execution proof.'))
assert len(png)==6 and len([n for n in entries if n.endswith('.png')])==6
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==h
assert subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
result=dict(source=h,owner_safe_sha256=sha(mr),owner_outer_readback_sha256=sha(orr),owner_candidates=[dict(path=n,bytes=e['bytes'],sha256=e['sha256'],transformation='none') for n,e in entries.items()],owner_candidate_count=38,owner_outer_count=2,maps=maps,map_bindings=9*1525,engineering_inputs=1525,distinct_final_git_blobs=len(set(x['git_blob'] for x in ref.values())),all_maps_git_mode_type_blob_size_sha_exact=True,runs=runs,screenshots=png,terminal_sentinels=terminal,first_original_dynamic_raw_status='LOST_NOT_RECONSTRUCTED',retained_run01='second accidental same-script execution; no Chrome; product NOT_RUN',run02_output_guards=['command.json','run-receipt.json','native.log','build.log'],missing_historical_guards=['failure.json','receipt.json'],first_attempt_hashes='Documentary/tool-derived only; lost original raw not independently reread/reconstructed.',native_scope='Learner awaiting-approval real Chrome/HTTP/SQLite/IDB only; running interrupt, independent/open-book Chrome, real CLI/model/tool and wholeM6.3 NOT_RUN/not accepted.',new_product_test_execution=False)
print(json.dumps(result,ensure_ascii=False,indent=2))
