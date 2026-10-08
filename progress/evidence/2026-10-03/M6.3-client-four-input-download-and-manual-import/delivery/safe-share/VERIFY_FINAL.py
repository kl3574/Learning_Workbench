"""Read-only private-package and fixed-source verification; never rewrites evidence."""
from pathlib import Path
import argparse, hashlib, json, subprocess
p = argparse.ArgumentParser(); p.add_argument('--repository', type=Path, required=True); a = p.parse_args()
e = Path(__file__).resolve().parent
sha = lambda x: hashlib.sha256(x).hexdigest()
raw = json.loads((e/'RAW_MANIFEST.json').read_text())
for f in raw['files']:
 data = (e/f['path']).read_bytes()
 assert sha(data) == f['sha256'] and len(data) == f['bytes'], f['path']
safe = json.loads((e/'SAFE_SHARE.json').read_text())
for f in safe['files']:
 source = (e/f['path']).read_bytes(); public = (e/'safe-share'/f['path']).read_bytes()
 assert public == source.replace(b'$HOME', b'$HOME'), f['path']
 assert sha(source) == f['raw_sha256'] and sha(public) == f['public_sha256'], f['path']
 assert source.count(b'$HOME') == f['exact_prefix_replacements'], f['path']
outer = json.loads((e/'PUBLIC_OUTER_ALLOWLIST.json').read_text())
for f in outer['files']:
 data=(e/f['path']).read_bytes(); assert sha(data)==f['sha256'] and len(data)==f['bytes']
source = json.loads((e/'FINAL_SOURCE_BINDINGS.json').read_text())
for f in source['files']:
 data = subprocess.check_output(['git','show',source['head']+':'+f['path']],cwd=a.repository)
 assert sha(data) == f['sha256'] and data == (e/'final-source'/f['path']).read_bytes(), f['path']
# Reconstruct expected digests from fixed Git blobs once, for all retained fixed gates.
cache = {}; gates=[]
for name in ['07-fixed-focused','08-native-static','09-native','10-full-web','12-fixed-native','13-fixed-full-web','14-fixed-strict','15-fixed-build','16-fixed-native-static','18-footer-fixed-focused','19-final-full-web','20-final-strict','21-final-full-native','22-final-build']:
 b=json.loads((e/name/'before.json').read_text()); c=json.loads((e/name/'after.json').read_text()); rec=json.loads((e/name/'receipt.json').read_text())
 assert b == c and b['status'] == '' and b['head'] == rec['source_head'] and b['all_exact_git'] and rec['inputs_unchanged'], name
 entries=subprocess.check_output(['git','ls-tree','-r','-z',b['head']],cwd=a.repository).split(b'\0')
 tree={x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0].split()[2].decode() for x in entries if x}
 tree={k:v for k,v in tree.items() if not k.startswith('progress/')}
 assert set(tree)=={f['path'] for f in b['files']} and len(tree)==b['count_nonprogress']==rec['count_nonprogress'],name
 for f in b['files']:
  blob=tree[f['path']]; assert blob==f['git_blob'] and f['exact_git'], (name,f['path'])
  if blob not in cache:
   data=subprocess.check_output(['git','cat-file','blob',blob],cwd=a.repository);cache[blob]=(sha(data),len(data))
  assert cache[blob]==(f['sha256'],f['bytes']), (name,f['path'])
 gates.append({'stage':name,'exit_code':rec['exit_code'],'count':len(tree)})
red=json.loads((e/'01-download-red/before.json').read_text());green=json.loads((e/'02-download-green/before.json').read_text())
key='apps/web/src/features/authoring/LocalTaskDocument.test.tsx'
old=next(f for f in red['files'] if f['path']==key);new=next(f for f in green['files'] if f['path']==key)
assert old['sha256']==new['sha256']==sha((e/'01-download-red/original-test.tsx').read_bytes())
aliases=json.loads((e/'PRIVATE_ALIAS_BINDINGS.json').read_text())
for item in aliases['files']:
 assert (e/item['raw_path']).read_bytes()==(e/item['alias']).read_bytes() and sha((e/item['alias']).read_bytes())==item['sha256']
final_alias=json.loads((e/'PRIVATE_FINAL_NATIVE_BINDINGS.json').read_text())
assert (e/final_alias['raw_path']).read_bytes()==(e/final_alias['alias']).read_bytes() and sha((e/final_alias['alias']).read_bytes())==final_alias['sha256']
print(json.dumps({'status':'PASS','raw_files':raw['count'],'safe_files':safe['count'],'outer_files':outer['count'],'fixed_gates':gates,'writes':0,'product_execution':False}))
