import datetime,hashlib,json,subprocess,time
from pathlib import Path
o=Path(__file__).parent
cmd=['bash','scripts/node.sh','node',str(o/'native.mjs')]
start=time.monotonic()
with (o/'run.log').open('wb') as log:r=subprocess.run(cmd,cwd='$HOME/.cache/learning-workbench-acceptance/m63-codex-turn-ui-cancel-binding-owner-oct04',stdout=log,stderr=subprocess.STDOUT)
v={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,'log_sha256':hashlib.sha256((o/'run.log').read_bytes()).hexdigest(),'scope':'Independent root native fixed-b149 actual execution; original db5 preflight/02/03 FAIL and04 limitedPASS retained. Includes full durable cancel ACK, loss/reload and exact original replay; explicit synthetic bootstrap, no model/CLI'}
(o/'COMMAND_READBACK.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v))
raise SystemExit(r.returncode)
