"""Read-only fixed Git/document and sealed evidence verification; no product execution."""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);args=p.parse_args()
E=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
bind=json.loads((E/'SOURCE_BINDINGS.json').read_text())
for x in bind['source_files']:
 b=subprocess.check_output(['git','show',x['commit']+':'+x['path']],cwd=args.repository)
 assert sha(b)==x['sha256'] and len(b)==x['bytes']
 assert subprocess.check_output(['git','rev-parse',x['commit']+':'+x['path']],cwd=args.repository,text=True).strip()==x['git_blob']
assert subprocess.check_output(['git','diff',bind['parent'],bind['head'],'--',bind['changed_paths'][0]],cwd=args.repository)==(E/bind['delta']['path']).read_bytes()
for x in bind['original_open_evidence']:
 b=(E.parent/x['directory']/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes']
raw=json.loads((E/'RAW_MANIFEST.json').read_text());safe=json.loads((E/'SAFE_SHARE.json').read_text());outer=json.loads((E/'PUBLIC_OUTER_ALLOWLIST.json').read_text())
assert raw['count']==len(raw['files']) and safe['count']==len(safe['files']) and outer['count']==len(outer['files'])
for x in raw['files']:
 b=(E/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256']
for x in safe['files']:
 b=(E/x['path']).read_bytes();d=(E/'safe-share'/x['path']).read_bytes();assert d==b.replace(b'$HOME',b'$HOME');assert sha(b)==x['raw_sha256'] and sha(d)==x['public_sha256']
for x in outer['files']:
 b=(E/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes']
print(json.dumps(dict(status='PASS',fixed_sources=len(bind['source_files']),raw_files=raw['count'],safe_files=safe['count'],outer_files=outer['count'],writes=0,network=False,product_execution=False)))
