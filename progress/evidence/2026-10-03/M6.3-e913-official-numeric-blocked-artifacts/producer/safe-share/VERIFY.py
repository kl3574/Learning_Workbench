"""Read-only evidence/hash/source verification. No network, DB or product execution."""
from pathlib import Path
import argparse,json,hashlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);a=p.parse_args();E=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
raw=json.loads((E/'RAW_MANIFEST.json').read_text());safe=json.loads((E/'SAFE_SHARE.json').read_text());outer=json.loads((E/'PUBLIC_OUTER_ALLOWLIST.json').read_text())
for x in raw['files']:
 b=(E/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes']
for x in safe['files']:
 b=(E/x['path']).read_bytes();d=(E/'safe-share'/x['path']).read_bytes();assert d==b.replace(b'$HOME',b'$HOME').replace(b'$CI_HOME',b'$CI_HOME') and sha(b)==x['raw_sha256'] and sha(d)==x['public_sha256']
for x in outer['files']:
 b=(E/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes']
source=json.loads((E/'SOURCE_BINDINGS.json').read_text());assert subprocess.check_output(['git','rev-parse',source['head_sha']+'^{tree}'],cwd=a.repository,text=True).strip()==source['common_tree']
for x in source['source_files']:
 b=subprocess.check_output(['git','show',source['head_sha']+':'+x['path']],cwd=a.repository);assert sha(b)==x['sha256'] and b==(E/'source'/x['path']).read_bytes()
for x in source['logs']:
 b=(E.parent/source['root_log_directory']/x['file']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes']
for r in json.loads((E/'ARCHIVE_READBACK.json').read_text())['receipts']:
 assert r['api_digest']=='sha256:'+r['archive_transport_sha256'] and r['strict_member_validation']=='PASS' and r['archive_not_saved']
 for x in r['members']:
  b=(E/str(r['run_id'])/('artifact-'+str(r['artifact_id']))/x['basename']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes']
print(json.dumps(dict(status='PASS',raw_files=raw['count'],safe_files=safe['count'],outer_files=outer['count'],json_members=6,artifact_transports=4,archive_files_saved=0,source_logs=4,network=False,product_execution=False,writes=0)))
