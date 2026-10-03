from pathlib import Path
import subprocess,json,hashlib,datetime,sys
r=Path('$HOME/.cache/learning-workbench-acceptance/m62-review-form-ci-diagnosis-oct02');out=Path(__file__).parent;name=sys.argv[1];d=out/name;d.mkdir(exist_ok=False)
paths=subprocess.check_output(['git','ls-files','-co','--exclude-standard'],cwd=r,text=True).splitlines();before={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in sorted(set(paths)) if not p.startswith('progress/') and (r/p).is_file()};(d/'before.json').write_text(json.dumps(before,indent=2)+'\n')
cmd=['env','TMPDIR=$HOME/.cache/m62-cr-tmp','LEARNING_E2E_OUTPUT_DIR='+str(d/'artifacts'),'bash','scripts/node.sh','npm','--prefix','apps/web','exec','--','playwright','test','--config',str(out/'playwright.config.mts'),'review-form-memory.spec.ts']
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (d/'run.log').open('wb') as f:p=subprocess.run(cmd,cwd=r,stdout=f,stderr=subprocess.STDOUT)
after={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in before};(d/'after.json').write_text(json.dumps(after,indent=2)+'\n');receipt={'command':cmd,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),'exit_code':p.returncode,'source_count':len(before),'unchanged':before==after,'log_sha256':hashlib.sha256((d/'run.log').read_bytes()).hexdigest()};(d/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print((d/'run.log').read_text()[-6000:]);print(json.dumps(receipt));raise SystemExit(p.returncode)
