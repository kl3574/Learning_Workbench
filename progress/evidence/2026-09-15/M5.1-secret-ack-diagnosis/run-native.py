from pathlib import Path
from datetime import datetime,timezone
import subprocess,os,sys,json,hashlib
root=Path('<REPO>'); cache=Path(__file__).parent
run,config=sys.argv[1:3]
path=cache/run;path.mkdir(exist_ok=False)
source_paths=['tests/e2e/provider-settings.spec.ts','apps/web/src/features/providers/useProviderSecret.ts','apps/web/src/features/providers/ProviderSecretPanel.tsx','apps/web/src/features/providers/ProviderSettings.tsx']
hashes=lambda:[{'path':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in source_paths]
started=datetime.now(timezone.utc).isoformat();before=hashes()
command=['bash','scripts/node.sh','npm','--prefix','apps/web','exec','--','playwright','test','--config',str(cache/config),'--grep',os.environ.get('SECRET_NATIVE_GREP','actual independent assessment policy'),'--output',str(path/'artifacts')]
env=os.environ.copy();env['TMPDIR']='<SYNTHETIC_TMPDIR>';Path(env['TMPDIR']).mkdir(exist_ok=True)
with (path/'run.log').open('w') as output: result=subprocess.run(command,cwd=root,env=env,stdout=output,stderr=subprocess.STDOUT)
receipt={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_code':result.returncode,'source_before':before,'source_after':hashes(),'configuration_sha256':hashlib.sha256((cache/config).read_bytes()).hexdigest(),'log_sha256':hashlib.sha256((path/'run.log').read_bytes()).hexdigest()}
(path/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('\n'.join(line for line in (path/'run.log').read_text().splitlines() if ' passed' in line or ' failed' in line or '✓' in line or '✘' in line));print(json.dumps({'run':run,'exit_code':result.returncode}))
