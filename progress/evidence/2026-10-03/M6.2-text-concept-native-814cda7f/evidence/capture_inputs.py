import hashlib,json,subprocess,sys
from pathlib import Path
root=Path("<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-text-concept-native-oct03")
evidence=Path(__file__).parent
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
paths=[p for p in subprocess.check_output(["git","ls-files","-z"],cwd=root).decode().split("\0") if p and not p.startswith("progress/")]
entries={}
for path in paths:
 data=(root/path).read_bytes(); original=subprocess.check_output(["git","show",head+":"+path],cwd=root)
 if data!=original: raise ValueError("source differs: "+path)
 entries[path]={"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
private={}
for path in ["capture_inputs.py","playwright-green-01.config.mts","tsconfig-native.json","playwright-runtime-types.d.ts"]:
 data=(evidence/path).read_bytes(); private[path]={"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
(evidence/sys.argv[1]).write_text(json.dumps({"head":head,"scope":"All Git-tracked non-progress files, exact Git bytes; progress and ignored runtime/tool files excluded. Actual private native config and typecheck sources separately listed.","count":len(entries),"tracked":entries,"private":private},indent=2)+"\n")
print(len(entries),"tracked non-progress inputs bound to",head)
