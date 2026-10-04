from pathlib import Path
import json,sys,hashlib,subprocess
O=Path(__file__).resolve().parent;B=O.parent;R=B/'m62-public-safe-oct02'
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();changes=[]
for p in ['progress/state.json','progress/CURRENT.md']:
 q=O/'before'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((R/p).read_bytes())
def safe(v,path='$'):
 if isinstance(v,dict):return {k:safe(x,path+'.'+k) for k,x in v.items()}
 if isinstance(v,list):return [safe(x,path+'['+str(i)+']') for i,x in enumerate(v)]
 if isinstance(v,str) and '$HOME' in v:
  b=v.encode();x=v.replace('$HOME','$HOME');changes.append({'JSON_path':path,'before_sha256':hashlib.sha256(b).hexdigest(),'after_sha256':hashlib.sha256(x.encode()).hexdigest(),'count':v.count('$HOME')});return x
 return v
s=safe(s);assert changes
s['verification']['m6_3_interrupt68a_original_documentary_publication_failure']={'status':'ACTUAL_ORIGINAL_FAIL_RETAINED','scope':'Originalstaged-publicationcheck exit1 namedstate/CURRENT personalprefix; no source/key/problem payload exposure claimed','repair':'Only literalpersonalHOMEprefix in newly embedded metadata replaced by $HOME for publication. Originalprivate commands/logs/receipt and digests not altered; normalized publicdocumentary paths are not executable original argv.','commit_precondition_failure':'One attempted commit guard FileNotFoundError missingpassedstageREADBACK; no commit occurred; originaltoolerror retained','required_followup':'Newstageddiff/publicationscan beforecommit; do not rewriteoriginalstageFAIL'}
save(s)
(O/'READBACK.json').write_text(json.dumps({'changed_string_paths':changes,'original_stage':'m63-interrupt68a-documentary-stage-oct05','original_scan_exit':1,'original_diff_exit':0,'private_original_docs_retained':True,'source_or_original_gate_logs_changed':False,'index_restaged_later':True},ensure_ascii=False,indent=2)+'\n')
print('Only'+str(sum(x['count'] for x in changes))+'literal personalHOME prefixes normalized at'+str(len(changes))+'structuredmetadata paths; originalFAIL retained.')
