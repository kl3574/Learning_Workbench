"""Read fixed Git objects and sealed files only; no application, test, DB or CLI runtime."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
repo=Path(sys.argv[2]) if len(sys.argv)>2 else root.parent/'m63-turn-dispatch-owner-oct04'
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
 assert not m.inspect('progress/evidence/dispatch/'+x['path'],p)
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
for stage in ['dispatch-related-final','dispatch-static-final']:
 a=read(stage+'/before.json');assert a['head']==src['final_head'] and a['count']==1417
 r=read(stage+'/receipt.json');assert r.get('exit_code',0)==0 and all(t['exit_code']==0 for t in r.get('results',[]))
assert '241 passed, 2 warnings in 196.40s' in (root/'dispatch-related-final/run.log').read_text()
origins=read('ORIGINS.json')
for item in origins['files']:
 original=root.parent/item['source_directory']/item['source_path']
 b=original.read_bytes();assert sha(b)==item['sha256'] and len(b)==item['bytes']
 assert b==(root/item['path']).read_bytes()
assert git('diff','--name-only',src['production_head'],src['final_head']).decode().splitlines()==['tests/integration/test_codex_turn_dispatch_http.py']
import ast
for probe in src['same_byte_counterexamples']:
 def body(head):
  value=git('show',head+':'+probe['path']).decode()
  node=next(n for n in ast.parse(value).body if isinstance(n,ast.FunctionDef) and n.name==probe['function'])
  return '\n'.join(value.splitlines()[node.lineno-1:node.end_lineno]).encode()
 assert body(probe['old_head'])==body(src['final_head']) and sha(body(src['final_head']))==probe['function_sha256']
expected={'start-red-01':1,'dispatch-expiry-red-fixed':1,'dispatch-first-fixed':0,'dispatch-missing-proof-red':1,'dispatch-second-fixed':0,'dispatch-third-fixed':1,'dispatch-related-final':0}
for stage,code in expected.items():
 receipt=read(stage+'/receipt.json');assert receipt['exit_code']==code and receipt['before_equals_after']
if '--skip-outer' not in sys.argv and (root/'PUBLIC_OUTER_ALLOWLIST.json').exists():
 for x in read('PUBLIC_OUTER_ALLOWLIST.json')['files']:
  b=(root/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes'];assert not m.inspect('progress/evidence/dispatch/'+x['path'],b)
print(json.dumps({'status':'PASS','raw_count':raw['count'],'safe_count':safe['count'],'fixed_maps':maps,'source_head':src['final_head'],'scope':'Read-only fixed Git and evidence; no runtime execution.'},indent=2))
