import datetime,hashlib,json,subprocess
from pathlib import Path
B=Path('$HOME/.cache/learning-workbench-acceptance');R=B/'m62-public-safe-oct02';G=B/'m63-generic-approval-static-fdd3a949-oct04';O=Path(__file__).parent
m=json.loads((G/'ENGINEERING_GIT_MANIFEST.json').read_text());expected={}
for item in subprocess.check_output(['git','ls-tree','-rz',m['commit']],cwd=R).split(b'\0'):
 if not item:continue
 meta,path=item.split(b'\t',1)
 if not path.startswith(b'progress/'):expected[path.decode()]=meta.split()[2].decode()
assert len(expected)==m['count']==1424 and set(expected)==set(m['files'])
p=subprocess.Popen(['git','cat-file','--batch'],cwd=R,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for name,e in m['files'].items():
 assert e['git_blob']==expected[name]
 p.stdin.write((e['git_blob']+'\n').encode());p.stdin.flush();h=p.stdout.readline().split()
 assert h[0].decode()==e['git_blob'] and h[1]==b'blob';blob=p.stdout.read(int(h[2]));assert p.stdout.read(1)==b'\n'
 assert len(blob)==e['bytes'] and hashlib.sha256(blob).hexdigest()==e['sha256']
p.stdin.close();assert p.wait()==0
report={'status':'ROOT_COMPLETE_FIXED_GENERIC_GIT_BLOB_READBACK_PASS','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixed_source':m['commit'],'actual_git_blob_count':1424,'all_nonprogress_paths_and_blob_hashes_verified':True,'manifest_sha256':hashlib.sha256((G/'ENGINEERING_GIT_MANIFEST.json').read_bytes()).hexdigest(),'boundary':'Only immutable Git source readback; no product tests or working-tree gate claim. Supplements initial native/generic candidate readback, whose generic scope was candidate hashes and manifest schema only.'}
(O/'GENERIC_GIT_READBACK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
