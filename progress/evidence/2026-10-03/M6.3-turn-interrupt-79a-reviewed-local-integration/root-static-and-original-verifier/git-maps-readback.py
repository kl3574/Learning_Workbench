import datetime,hashlib,json,subprocess
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance');O=Path(__file__).parent;E=B/'m63-turn-interrupt-evidence-oct04';R=B/'m63-turn-interrupt-owner-oct04';H='79a3c0da4bef9d948bcd6a969a25ff55fd5833a0';sha=lambda b:hashlib.sha256(b).hexdigest()
assert not (O/'FINAL_MAPS_READBACK.json').exists();stages=['related-79a3','ruff-79a3','mypy-79a3','generated-79a3','spec-79a3','ts-79a3'];maps=[];expected={}
for item in subprocess.check_output(['git','ls-tree','-rz',H],cwd=R).split(b'\0'):
 if not item:continue
 meta,name=item.split(b'\t',1)
 if not name.startswith(b'progress/'):expected[name.decode()]=meta.split()[2].decode()
assert len(expected)==1428
for stage in stages:
 raw=(E/stage/'inputs-before.json').read_bytes();assert raw==(E/stage/'inputs-after.json').read_bytes();d=json.loads(raw);assert set(d)==set(expected)
 for name,e in d.items():assert e['git_exact']
 maps.append({'stage':stage,'count':len(d),'sha256':sha(raw)})
d=json.loads((E/stages[0]/'inputs-before.json').read_text());p=subprocess.Popen(['git','cat-file','--batch'],cwd=R,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for name,oid in expected.items():
 p.stdin.write((oid+'\n').encode());p.stdin.flush();h=p.stdout.readline().split();blob=p.stdout.read(int(h[2]));assert p.stdout.read(1)==b'\n';assert sha(blob)==d[name]['sha256'] and len(blob)==d[name]['bytes']
 assert (R/name).read_bytes()==blob
p.stdin.close();assert p.wait()==0
for stage in stages[1:]:assert json.loads((E/stage/'inputs-before.json').read_text())==d
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==H and not subprocess.check_output(['git','status','--porcelain'],cwd=R)
for stage in stages:
 r=json.loads((E/stage/'receipt.json').read_text());assert r['head']==H and r['exit']==0 and r['git_exact'] and r['unchanged'];assert r['log_sha256']==sha((E/stage/'run.log').read_bytes())
assert b'1160 passed' in (E/'related-79a3/run.log').read_bytes()
report={'status':'ROOT_INTERRUPT_COMPLETE_FIXED_GIT_MAP_AND_LOG_READBACK_PASS','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':H,'complete_git_count':1428,'all_six_before_after_maps_equal_and_all_blob_hashes_verified':True,'maps':maps,'author_related_tests':'1160PASS/2warnings, rootreadlog only','original_root_schema_failure':'First extra inspection treated flatmap as nested files/inputs; KeyError retained as separateharness observation. Originalpurehashverifier alreadyexit0 and itsreceipt unchanged. No product failed or executed during that inspection.','boundary':'Read-only source/evidence verification, no tests/CLI/model, originalthreeRED and allfailures retained; independentreviewP3 task_id deviation preserved, no wholeM6.3 acceptance.'};(O/'FINAL_MAPS_READBACK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'count':1428,'maps':6,'sha256':sha((O/'FINAL_MAPS_READBACK.json').read_bytes())}))
