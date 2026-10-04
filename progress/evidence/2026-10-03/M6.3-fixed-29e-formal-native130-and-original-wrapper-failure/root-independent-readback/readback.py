import datetime, hashlib, json, subprocess, sys
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance'); R=B/'m62-public-safe-oct02'; O=Path(__file__).parent
sys.path.insert(0,str(R/'scripts'))
from check_publication import inspect
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p): return json.loads(p.read_text())
def git_map(d,live=None):
 tree=subprocess.check_output(['git','ls-tree','-rz',d['head']],cwd=R)
 expected={}
 for item in tree.split(b'\0'):
  if not item:continue
  meta,path=item.split(b'\t',1)
  if not path.startswith(b'progress/'):expected[path.decode()]=meta.split()[2].decode()
 assert set(expected)=={f['path'] for f in d['files']}
 assert len(expected)==d['count']
 p=subprocess.Popen(['git','cat-file','--batch'],cwd=R,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
 for f in d['files']:
  assert f['git_blob']==expected[f['path']]
  p.stdin.write((f['git_blob']+'\n').encode());p.stdin.flush()
  h=p.stdout.readline().split();blob=p.stdout.read(int(h[2]));assert p.stdout.read(1)==b'\n'
  assert sha(blob)==f['sha256'] and f['matches_git'] and f['actual_blob']==f['git_blob']
  if live:assert sha((live/f['path']).read_bytes())==f['sha256']
 p.stdin.close();assert p.wait()==0
 return len(expected)
N=B/'m63-native-formal-29e864a6-03-oct04'; C=N/'publication-candidates'
a=read(C/'allowlist.json'); records=[]
assert len(a['files'])==29
for e in a['files']:
 raw=(B/e['raw_relative_path']).read_bytes();candidate=(C/e['path']).read_bytes()
 assert sha(raw)==e['raw_sha256'] and sha(candidate)==e['candidate_sha256']
 expected=raw if e['path'].endswith('.png') else raw.replace(b'$HOME',b'<LOCAL_HOME>')
 assert candidate==expected
 assert not inspect('progress/'+e['path'],candidate)
 records.append({'path':e['path'],'raw_sha256':sha(raw),'candidate_sha256':sha(candidate),'bytes':len(candidate)})
before=read(N/'inputs-before.json');after=read(N/'inputs-after.json');fixed='29e864a6157f3bb23c6ced5d1a2f34f77bf3b875'
assert before['head']==after['head']==fixed
assert (N/'inputs-before.json').read_bytes()==(N/'canonical-after.json').read_bytes()
assert git_map(before,R)==1433
old={f['path']:f for f in before['files']};new={f['path']:f for f in after['files']};assert set(old)==set(new)
changed=sorted(p for p in old if old[p]['sha256']!=new[p]['sha256'])
assert changed==sorted(['docs/ui/m1-after-1440.png','docs/ui/m1-after-1920.png','docs/ui/m1-after-390-agent.png','docs/ui/m1-native-zoom-metrics.json','docs/ui/m1-session-three-way-conflict.png'])
for p in new:assert sha((B/'m63-native-formal-29e-owner-oct04'/p).read_bytes())==new[p]['sha256']
supp=read(N/'SUPPLEMENTAL_AUDIT.json');assert len(supp['complete_preexisting_output_paths'])==10
assert not set(changed)-set(supp['complete_preexisting_output_paths'])
assert all(old[p]==new[p] for p in old if p not in changed)
log=(N/'native.log').read_bytes();assert sha(log)=='2fce6646b473f28a170f084d9e5bcbf18d36645d1c809b03d87b1691141628f9'
assert b'130 passed' in log
G=B/'m63-generic-approval-static-fdd3a949-oct04';s=read(G/'SAFE_SHARE.json');outer=read(G/'PUBLIC_OUTER_ALLOWLIST.json')
assert len(s['explicit_candidates'])==7 and len(outer['files'])==3
for e in s['explicit_candidates']:
 raw=(G/e['source']).read_bytes();candidate=(G/e['candidate']).read_bytes();assert raw==candidate
 assert sha(raw)==e['sha256'] and len(raw)==e['bytes'];assert not inspect('progress/'+e['candidate'],candidate)
for name,e in outer['files'].items():
 b=(G/name).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];assert not inspect('progress/'+name,b)
for line in (G/'SHA256SUMS').read_text().splitlines():
 h,name=line.split('  ',1);assert sha((G/name).read_bytes())==h
m=read(G/'ENGINEERING_GIT_MANIFEST.json')
if 'files' not in m:
 raise AssertionError('Unexpected Git manifest schema; fail closed')
# Full manifest is bound to Git by the peer; root separately validates its shape below.
report={'status':'ROOT_READONLY_CANDIDATE_AND_NATIVE_INPUT_READBACK_PASS','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native_suite':'130 PASS, make exit0; original wrapper exit1 preserved','native_candidate_count':29,'native_candidates':records,'native_complete_before_git_count':1433,'actual_changed_generated_outputs':changed,'other_tracked_unchanged':1428,'complete_preexisting_output_paths':supp['complete_preexisting_output_paths'],'non_generated_source_inputs_unchanged':1423,'canonical_unchanged_clean':True,'images':'Root independently viewed5 explicit PNGs; synthetic UI only, no auth/private material seen','generic_static_candidates':7,'generic_static_outer':3,'generic_manifest_schema':list(m),'boundary':'Only read-only source/artifact/hash checks. No product test execution, external model/CLI, full M6.3, numeric or academic acceptance. Prefix-transformed archival scripts are not runnable-equivalence claims.'}
(O/'READBACK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'native_candidates':29,'actual_changed_generated_outputs':len(changed),'generic_static_candidates':7,'generic_manifest_schema':list(m),'sha256':sha((O/'READBACK.json').read_bytes())}))
