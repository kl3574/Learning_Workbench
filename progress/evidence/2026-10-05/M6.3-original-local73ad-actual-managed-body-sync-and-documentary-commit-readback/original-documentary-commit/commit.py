import datetime,hashlib,json,subprocess
from pathlib import Path
b=Path('$HOME/.cache/learning-workbench-acceptance');r=b/'m62-public-safe-oct02';o=Path(__file__).parent
head='8e1ad259f3dd5ea7cdc85456351b27b2e4412249'
def g(*a):return subprocess.check_output(['git',*a],cwd=r)
assert g('rev-parse','HEAD').decode().strip()==head
check=json.loads((b/'m63-interrupt68a-documentary-stage-corrected-oct05/READBACK.json').read_text());assert check['selected_count']==416 and check['staged_publication_exit']==0
selection=json.loads((b/'m63-interrupt68a-documentary-stage-corrected-oct05/SELECTION.json').read_text())['files'];assert sorted(g('diff','--cached','--name-only').decode().splitlines())==sorted(selection)
assert not g('diff','--name-only') and not g('ls-files','--others','--exclude-standard')
argv=['git','commit','-m','Record interrupt pairing repair and actual failed gates with new complete gate start']
(o/'command.json').write_text(json.dumps({'argv':argv,'cwd':str(r),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
x=subprocess.run(argv,cwd=r,capture_output=True);(o/'stdout').write_bytes(x.stdout);(o/'stderr').write_bytes(x.stderr)
(o/'receipt.json').write_text(json.dumps({'exit_code':x.returncode,'stdout_sha256':hashlib.sha256(x.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(x.stderr).hexdigest(),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
assert x.returncode==0
new=g('rev-parse','HEAD').decode().strip();assert not g('status','--porcelain') and g('rev-parse','HEAD^').decode().strip()==head
assert len(g('diff','--name-only',head,new).decode().splitlines())==416
result={'new_head':new,'parent':head,'documentary_paths':416,'source_engineering_unchanged':not g('diff','--name-only',head,new,'--','.',':(exclude)progress/**'),'clean':True,'public_head':'1e7ad7a8656c0dc8373d4181fa3002f385ed1847','sourcepush':False,'CI_old_originals':'eachbrowser131PASS2FAIL/integrationstillrunning; NOT fullPASS','wholeM6_3':'NOT_ACCEPTED'}
(o/'READBACK.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
