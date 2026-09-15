import datetime, hashlib, json, os, pathlib, subprocess, sys
root=pathlib.Path('<private-home>/Desktop/learning/Learning_Workbench')
base=pathlib.Path(__file__).parent
name=sys.argv[1]; out=base/name; out.mkdir()
files=['apps/web/src/workbench/Shell.tsx','tests/e2e/import-admission.spec.ts','tests/e2e/reader.spec.ts','tests/e2e/helpers.ts','tests/e2e/playwright.config.ts','PRODUCT_DESIGN.md']
def inventory(): return {v:hashlib.sha256((root/v).read_bytes()).hexdigest() for v in files}
before=inventory()
for v in files[:3]: (out/(pathlib.Path(v).name+'.txt')).write_bytes((root/v).read_bytes())
env=dict(os.environ); env['TMPDIR']='<private-home>/.cache/lw-m42-root'; pathlib.Path(env['TMPDIR']).mkdir(exist_ok=True); env.pop('LEARNING_E2E_DATA_DIR',None); env['LEARNING_E2E_OUTPUT_DIR']=str(out/'artifacts')
command=['bash','scripts/node.sh','npm','--prefix','apps/web','run','test:e2e','--',*sys.argv[2:]]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (out/'run.log').open('wb') as log: result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
after=inventory(); receipt={'command':command,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':result.returncode,'source_before':before,'source_after':after,'inputs_unchanged':before==after,'log_sha256':hashlib.sha256((out/'run.log').read_bytes()).hexdigest()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print((out/'run.log').read_text()); print('receipt',out/'receipt.json'); sys.exit(result.returncode)
