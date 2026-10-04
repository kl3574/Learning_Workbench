"""Read fixed Git objects and sealed files only; no application, test, DB or CLI runtime."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
repo=Path(sys.argv[2]) if len(sys.argv)>2 else root.parent/'m63-turn-grant-owner-oct04'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads((root/p).read_text())
def git(*a):return subprocess.check_output(['git',*a],cwd=repo)
raw=read('RAW_MANIFEST.json');safe=read('SAFE_SHARE.json')
assert raw['count']==len(raw['files'])==len({x['path'] for x in raw['files']})
assert safe['count']==len(safe['files'])
for x in raw['files']:
 b=(root/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'],x['path']
s=importlib.util.spec_from_file_location('scanner',repo/'scripts/check_publication.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for x in safe['files']:
 b=(root/x['path']).read_bytes();p=(root/'safe-share'/x['path']).read_bytes()
 assert sha(b)==x['raw_sha256'] and len(b)==x['raw_bytes']
 assert p==b.replace(bytes([47,104,111,109,101,47,108,107,120]),b'$HOME') and sha(p)==x['public_sha256'] and len(p)==x['public_bytes']
 assert not m.inspect('progress/evidence/grant/'+x['path'],p)
 assert not re.search(rb'(?i)(authorization|x-csrf-token|cookie)[\"\x27]?\s*[:=]\s*[\"\x27]?[A-Za-z0-9_+/=-]{16,}',p)
cache={};maps=[]
def blob(h):
 if h not in cache:cache[h]=git('cat-file','blob',h)
 return cache[h]
for x in raw['files']:
 if not x['path'].endswith('/before.json'):continue
 a=read(x['path']);z=read(x['path'].replace('/before.json','/after.json'));assert a==z and a['all_exact'] and not a['status']
 tree={}
 for row in git('ls-tree','-r','-z',a['head']).split(b'\0'):
  if not row:continue
  meta,p=row.split(b'\t');p=p.decode()
  if not p.startswith('progress/'):tree[p]=meta.decode().split()[2]
 assert len(tree)==a['count'] and set(tree)==set(a['inputs'])
 for p,item in a['inputs'].items():
  assert item.get('git_blob',tree[p])==tree[p] and item['equal'];b=blob(tree[p])
  assert sha(b)==item['sha256']==item['git_sha256'] and len(b)==item['size']
 maps.append({'path':x['path'],'head':a['head'],'count':a['count']})
src=read('SOURCE_BINDINGS.json');assert git('rev-parse',src['final_head']+'^{tree}').decode().strip()==src['final_tree']
assert sha(git('show',src['final_head']+':PRODUCT_DESIGN.md'))==src['spec_sha256']
for p,x in src['changed_paths'].items():
 assert git('rev-parse',src['final_head']+':'+p).decode().strip()==x['git_blob'];b=blob(x['git_blob']);assert sha(b)==x['sha256'] and len(b)==x['bytes']
for stage in ['permit-fixed-03','permit-static-03']:
 a=read(stage+'/before.json');assert a['head']==src['final_head'] and a['count']==1413
 r=read(stage+'/receipt.json');assert r.get('exit_code',0)==0 and all(t['exit_code']==0 for t in r.get('results',[]))
assert '81 passed, 2 warnings in 76.44s' in (root/'permit-fixed-03/run.log').read_text()
if '--skip-outer' not in sys.argv and (root/'PUBLIC_OUTER_ALLOWLIST.json').exists():
 for x in read('PUBLIC_OUTER_ALLOWLIST.json')['files']:
  b=(root/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes'];assert not m.inspect('progress/evidence/grant/'+x['path'],b)
print(json.dumps({'status':'PASS','raw_count':raw['count'],'safe_count':safe['count'],'fixed_maps':maps,'source_head':src['final_head'],'scope':'Read-only fixed Git and evidence; no runtime execution.'},indent=2))
