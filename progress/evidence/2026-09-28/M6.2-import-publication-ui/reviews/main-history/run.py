from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess
base=Path(__file__).resolve().parent
source=base.parent/'m62-active'
bare=base.parent/'m62-import-publication-ui-main-history-bare.git'
public=base.parent/'m62-import-publication-ui-public-v1/public'
main='4a5c6de3b74fdc1659389326c746e05ef19ff00b'
private='fa71351e7d6b9358d4b0ef2f46184999f84e5e08'
assert not bare.exists()
started=datetime.now(timezone.utc).isoformat();commands=[]
with (base/'run.log').open('wb') as stream:
 def run(args,expected=0):
  stream.write(('COMMAND '+json.dumps(args)+'\n').encode());stream.flush()
  result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  stream.write(result.stdout);stream.write(('EXIT '+str(result.returncode)+'\n').encode());stream.flush()
  commands.append({'argv':args,'exit_code':result.returncode,'output_sha256':hashlib.sha256(result.stdout).hexdigest()})
  assert result.returncode==expected,(args,result.returncode)
  return result.stdout
 run(['git','init','--bare','--initial-branch=main',str(bare)])
 run(['git','-C',str(bare),'fetch','--no-tags',str(source),main+':refs/heads/main'])
 run(['git','-C',str(bare),'cat-file','-e',private],128)
 refs=run(['git','-C',str(bare),'show-ref']).decode().splitlines()
 assert refs==[main+' refs/heads/main']
 output=run(['python',str(public/'verify.py'),'--source-repo',str(bare),'--public-main',main])
 verification=json.loads(output);assert verification['status']=='PASS' and verification['public_main_verified']==main
 assert len(verification['stage_coverage'])==22
 (base/'VERIFIER_OUTPUT.json').write_bytes(output)
manifest=public/'manifest.json'
receipt={'scope':'Empty bare initialized, only exact local main history fetched; private fa713 Git object absent (expected cat-file exit128). Local main-only portability, not remote publication proof.','started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'main':main,'private_candidate':private,'private_object_absent':True,'refs':refs,'commands':commands,'public_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'verifier_sha256':hashlib.sha256((public/'verify.py').read_bytes()).hexdigest(),'log_sha256':hashlib.sha256((base/'run.log').read_bytes()).hexdigest(),'result':'PASS','network_remote_access':False,'product_tests_run':False}
(base/'TASK_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':'PASS','main':main,'private_object_absent':True,'stages':len(verification['stage_coverage']),'refs':refs,'public_manifest_sha256':receipt['public_manifest_sha256'],'scope':receipt['scope']}))
