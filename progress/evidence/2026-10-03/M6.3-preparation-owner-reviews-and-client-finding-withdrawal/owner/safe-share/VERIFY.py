"""Read sealed evidence/Git only. No application, database, tests or CLI runtime."""
import hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
repo=Path(sys.argv[2]) if len(sys.argv)>2 else root.parent/'m63-turn-preparation-owner-oct04'
def sha(data): return hashlib.sha256(data).hexdigest()
def read(name): return json.loads((root/name).read_text())
def git(*args): return subprocess.check_output(['git',*args],cwd=repo)
raw=read('RAW_MANIFEST.json'); safe=read('SAFE_SHARE.json')
assert raw['count']==len(raw['files']) and safe['count']==len(safe['files'])
assert len({v['path'] for v in raw['files']})==raw['count']
for item in raw['files']:
 data=(root/item['path']).read_bytes(); assert len(data)==item['bytes'] and sha(data)==item['sha256'],item['path']
spec=importlib.util.spec_from_file_location('publication_scanner',repo/'scripts/check_publication.py')
scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
for item in safe['files']:
 data=(root/item['path']).read_bytes(); public=(root/'safe-share'/item['path']).read_bytes()
 assert sha(data)==item['raw_sha256'] and len(data)==item['raw_bytes']
 assert public==data.replace(b'$HOME',b'$HOME') and sha(public)==item['public_sha256'] and len(public)==item['public_bytes']
 assert not scanner.inspect('progress/evidence/review/'+item['path'],public),item['path']
 assert not re.search(rb'(?i)(?:authorization|x-csrf-token|cookie)[\"\x27]?\s*[:=]\s*[\"\x27]?[A-Za-z0-9_+/=-]{16,}',public),item['path']
cache={}; maps=[]
def blob(key):
 if key not in cache:cache[key]=git('cat-file','blob',key)
 return cache[key]
for item in raw['files']:
 if not item['path'].endswith('/before.json'):continue
 before=read(item['path']);head=before['head']
 tree={}
 for entry in git('ls-tree','-r','-z',head).split(b'\0'):
  if not entry:continue
  meta,name=entry.split(b'\t');name=name.decode()
  if not name.startswith('progress/'):tree[name]=meta.decode().split()[2]
 assert set(tree)==set(before['inputs']) and before['count']==len(tree) and before['all_exact'] and not before['status']
 for path,binding in before['inputs'].items():
  assert tree[path]==binding['git_blob'] and binding['equal']
  data=blob(binding['git_blob']);assert sha(data)==binding['sha256']==binding['git_sha256'] and len(data)==binding['size']
 after_path=item['path'].replace('/before.json','/after.json')
 if (root/after_path).exists():assert before==read(after_path)
 maps.append({'path':item['path'],'head':head,'count':len(tree),'has_after':(root/after_path).exists()})
binding=read('SOURCE_BINDINGS.json')
if 'final_head' in binding:
 assert git('rev-parse',binding['final_head']+'^{tree}').decode().strip()==binding['final_tree']
 for path,item in binding['changed_paths'].items():
  assert git('rev-parse',binding['final_head']+':'+path).decode().strip()==item['git_blob']
  assert sha(blob(item['git_blob']))==item['sha256']
 for stage in ['related-final','static-final']:
  r=read(stage+'/receipt.json');assert r['head']==binding['final_head'] and r['source_count']==1403 and r['before_equals_after']
  assert r.get('exit_code',0)==0 and all(c['exit_code']==0 for c in r.get('commands',[]))
 assert '416 passed, 2 warnings in 234.02s' in (root/'related-final/run.log').read_text()
 probe=binding['counterexamples'];p=probe['probe_path']
 assert sha(git('show',probe['old_source_head']+':'+p))==sha(git('show',binding['final_head']+':'+p))==probe['probe_sha256']
else:
 for path,item in binding['selected_sources'].items():assert sha(git('show',binding['head']+':'+path))==item['sha256']
 for path in binding['unchanged_legacy_paths']:assert git('show',binding['base']+':'+path)==git('show',binding['head']+':'+path)
 assert len(binding['changed_paths'])==4
outer=root/'PUBLIC_OUTER_ALLOWLIST.json'
if outer.exists():
 for item in read(outer.name)['files']:
  data=(root/item['path']).read_bytes(); assert sha(data)==item['sha256'] and len(data)==item['bytes']
  assert not scanner.inspect('progress/evidence/review/'+item['path'],data)
print(json.dumps({'status':'PASS','raw_files':raw['count'],'safe_files':safe['count'],'maps':maps,'operation_scope':'read-only files and fixed Git objects; zero application/test/DB/CLI/model operations'},indent=2))
