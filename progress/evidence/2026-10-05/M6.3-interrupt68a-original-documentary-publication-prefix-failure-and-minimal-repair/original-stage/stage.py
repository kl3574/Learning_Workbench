import datetime,hashlib,json,subprocess
from pathlib import Path
b=Path('$HOME/.cache/learning-workbench-acceptance');r=b/'m62-public-safe-oct02';o=Path(__file__).parent
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=r).decode().strip()=='8e1ad259f3dd5ea7cdc85456351b27b2e4412249'
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=r)
files=['progress/state.json','progress/CURRENT.md','progress/M6.3-next.md','progress/M6.3-bootstrap-acceptance.md']
extra=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=r).decode().splitlines()
prefixes=['M6.3-catalog27f-actual-Node-setup-failure-and-correctly-bound-scoped-recheck','M6.3-interrupt-RPC68a-original-failures-fixed-gates-and-independent-seal','M6.3-public1e7ad-actual-sourcepush-and-bounded-publication-audit','M6.3-public1e7ad-original-actual-managed-Issue32-and-draftPR56-body-sync','M6.3-original27f-complete-Python-actual-six-Node-failures-and-independent-terminal','M6.3-public1e7ad-original-browser-failures-independent-logs-and-actual-artifact-readback','M6.3-new68a-locked-environment-original-complete-Python-actual-start-and-preparation']
assert len(extra)==394 and all(any(x.startswith('progress/evidence/2026-10-05/'+n+'/') for n in prefixes) for x in extra)
files+=extra
(o/'SELECTION.json').write_text(json.dumps({'files':files,'count':len(files),'source':'8e1ad259f3dd5ea7cdc85456351b27b2e4412249','scope':'Exact four currentprogress documents andseven explicit finite evidence packages'},indent=2)+'\n')
def run(name,argv):
 (o/(name+'-command.json')).write_text(json.dumps({'argv':argv,'cwd':str(r),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
 x=subprocess.run(argv,cwd=r,capture_output=True);(o/(name+'.stdout')).write_bytes(x.stdout);(o/(name+'.stderr')).write_bytes(x.stderr)
 (o/(name+'-receipt.json')).write_text(json.dumps({'exit_code':x.returncode,'stdout_sha256':hashlib.sha256(x.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(x.stderr).hexdigest(),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
 assert x.returncode==0,(name,x.returncode)
run('stage',['git','add','--',*files])
run('original-staged-diff',['git','diff','--cached','--check'])
run('staged-publication',['uv','run','--frozen','--no-sync','python','scripts/check_publication.py'])
(o/'READBACK.json').write_text(json.dumps({'selected_count':len(files),'staged_diff_exit':0,'staged_publication_exit':0,'source_push':False,'github_merge':False,'wholeM6_3':'NOT_ACCEPTED'},indent=2)+'\n')
print('Exact398files staged; originaldiff/publicationscan passed; no commit or push yet.')
