from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(sys.argv[1]); output=Path(sys.argv[2])
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
entries=subprocess.check_output(['git','ls-tree','-rz','--full-tree',head],cwd=root).split(b'\0')
files=[]
for entry in entries:
    if not entry: continue
    meta,name=entry.split(b'\t',1);path=name.decode();mode,kind,blob=meta.decode().split()
    if path.startswith('progress/') or kind!='blob': continue
    raw=(root/path).read_bytes()
    actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    files.append({'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_blob':blob,'git_matches':actual==blob})
result={'head':head,'tracked_status':subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True),
    'scope':'All Git tracked non-progress blobs; dependencies/temporary databases excluded','input_count':len(files),
    'all_git_matches':all(item['git_matches'] for item in files),'inputs':files}
output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key!='inputs'}))
