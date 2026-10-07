from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
O=Path(__file__).resolve().parent;B=O.parent;E=B/'m63-public079-early-eight-job-independent-oct07';C=B/'m63-ci-public079a008-observation-oct07';R=B/'m62-public-safe-oct02'
def sha(b):return hashlib.sha256(b).hexdigest()
assert sha((E/'SEAL.json').read_bytes())=='b6cefdf04d237bbaa193a648716511d1a5b868b6385705cfbbf53374c0b76dc8'
assert sha((E/'SAFE-CANDIDATE-MANIFEST.json').read_bytes())=='78a9da7cc6c8003ff204ec034a0bfe98344aa2396ce7be927826f8c02338414a'
seal=json.loads((E/'SEAL.json').read_bytes());manifest=json.loads((E/'SAFE-CANDIDATE-MANIFEST.json').read_bytes())
sys.path.insert(0,str(R/'scripts'));from check_publication import inspect
for e in seal['outputs']:
 b=(E/e['file']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256']
 assert not inspect('progress/'+e['file'],b.replace(b'$HOME',b'$HOME').replace(b'$RUNNER_HOME',b'$RUNNER_HOME'))
total=0;rows=[]
for e in manifest['candidates']:
 raw=(C/e['source_file']).read_bytes();assert sha(raw)==e['source_stdout_sha256']
 stem='job-'+str(e['job_id'])+'-logs-01';cmd=json.loads((C/(stem+'-command.json')).read_bytes());rcpt=json.loads((C/(stem+'-receipt.json')).read_bytes())
 assert cmd['run_id']==e['run_id'] and cmd['event']==e['event'] and cmd['run_attempt']==1
 assert rcpt['exit_code']==0 and rcpt['stdout_sha256']==sha(raw) and rcpt['stdout_bytes']==len(raw)
 err=(C/(stem+'.stderr')).read_bytes();assert err==b'' and sha(err)==rcpt['stderr_sha256']
 lines=raw.splitlines(keepends=True);selected=[]
 for line in e['selected_lines']:
  b=lines[line['source_line']-1];assert len(b)==line['original_line_bytes'] and sha(b)==line['original_line_sha256'];selected.append(b)
 candidate=(E/e['candidate_file']).read_bytes();assert candidate==b''.join(selected) and len(candidate)==e['bytes'] and sha(candidate)==e['sha256']
 assert not inspect('progress/'+e['candidate_file'],candidate);total+=len(selected)
 rows.append({'job_id':e['job_id'],'run_id':e['run_id'],'event':e['event'],'raw_size':len(raw),'raw_sha256':sha(raw),'candidate_lines':len(selected),'candidate_sha256':sha(candidate)})
assert len(rows)==8 and total==120
snap=json.loads((C/'14-SNAPSHOT.json').read_bytes());assert snap['source']=='079a008cf88b37e4517cb391503a1e7393ccf374'
assert all(e['status']=='in_progress' and sum(j['conclusion']=='success' for j in e['jobs'])==4 for e in snap['actual_events'])
(O/'ROOT_ADMISSION.json').write_text(json.dumps({'scope':'Root independent13finite outputs/8raw hashes and originalcapturemetadata/120exactselectedlines; complete owner4783B report read, no originalwhole8raw semantic reread',
 'source':snap['source'],'original_snapshot':14,'original_early_status':'BOTH4SUCCESS2RUNNING_NOT_TERMINAL','bindings':rows,'safe_original_line_count':120,
 'actual_each_event':'backend1114P3warnings/mypy295/Ruff0;frontend1421P167files/build879modules;spec962P2warnings/M0structureonly;publication23175/manual provenance required',
 'warnings':'Originalnpm4vulnerabilities3low1high/Vitechunk/jsdomadvisory retained; dependencydiagnosis separate NOT_IMPLEMENTED_IN_THIS_PACKET',
 'limits':['CIworkinginputbeforeafterNOT_CAPTURED','Original8raw reviewed independentlybyowner; root qualifications restricted to exactfinite excerpts/metadata','Remainingbrowser/integration/newcompletePy/wholeCI/model/M6.3NOT_ACCEPTED','No rerun/cancel/network/remote mutation or privatepayload/ZIP/DB/profile read']},indent=2)+'\n')
sp=importlib.util.spec_from_file_location('helper',B/'m63-public079a008-progress-record-oct07/package-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
path=h.package('M6.3-public079-original-eight-completed-jobs-independent-finite-readback',[
 ('independent-finite',E.name,[e['file'] for e in seal['outputs']]+['SEAL.json']),('root-original-line-admission',O.name,['verify.py','ROOT_ADMISSION.json'])],
 {'scope':'Originalearly8completedjobs only;120exactoriginalsafe lines independently bound; originalfullraw/API excluded',
 'source':snap['source'],'snapshot':14,'original_events':[37632652743,37632662238],'actual_each_event':'1114backendP/3warn/mypy295;1421frontendP/167files;962specP/2warn;23175publicationpaths/manual provenance',
 'original_each_event_status':'4SUCCESS2RUNNING_NO_TERMINAL','warning_actual':'npm4vulnerabilities3low1high retained; diagnosis separate',
 'CIworkingmaps':'NOT_CAPTURED','whole_CI_M63_AC21_M7':'NOT_ACCEPTED','model_calls':0,'remote_write':False})
sys.path.insert(0,str(R/'scripts'));from progress import read_state,save
s=read_state();t=next(x for x in s['tasks'] if x['id']=='M6.3');t['evidence_paths'].append(path)
s['verification']['m6_3_public079_original_early8_qualified']={'evidence':path,'source':snap['source'],'snapshot':14,'each_event':'backend1114PASS3warnings/mypy295/Ruff0;frontend1421PASS167files;spec962PASS2warnings;scanner23175/manualprovenance','workingmaps':'NOT_CAPTURED','wholeCI':'NOT_TERMINAL','current_dependency_notice':'1high3low npm notice under isolateddiagnosis; no fix yet'}
save(s)
(O/'INSTALL_READBACK.json').write_text(json.dumps({'evidence':path,'finite_originals':8,'selected_lines':120,'whole_CI':'NOT_TERMINAL','sourcepush':False},indent=2)+'\n')
print('Qualified exact120safeoriginal lines and finite8jobreport; fullCI/workingmaps/actualmodel acceptance notborrowed.')
