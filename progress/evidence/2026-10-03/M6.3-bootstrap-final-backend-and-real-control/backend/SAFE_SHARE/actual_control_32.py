"""One explicitly approved synthetic-workspace HTTP command using real fixed control runtime.
No account read, model turn, tool, global config or credential access. Public result is an allowlist.
"""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path('$HOME/.cache/learning-workbench-acceptance/m63-local-session-bootstrap-implementation-oct03')
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import issue_bootstrap_code
from services.api.app.infrastructure import codex_bootstrap_runtime as runtime_module
OUT=Path(__file__).parent/'actual-32'
OUT.mkdir(mode=0o700,exist_ok=False)
located=shutil.which('codex')
assert located is not None
settings=Settings(data_dir=OUT/'private-workspace',codex_executable=Path(located).resolve())
app=create_app(settings)
app.state.database.initialize()
client=TestClient(app,base_url=settings.origin)
response=client.post('/api/v1/session/bootstrap',json={'one_time_code':issue_bootstrap_code(app.state.database)},headers={'Origin':settings.origin})
assert response.status_code==200
headers={'Origin':settings.origin,'X-CSRF-Token':response.json()['csrf_token']}
assert client.post('/api/v1/session/role',json={'role':'author'},headers={**headers,'Idempotency-Key':'synthetic-author'}).status_code==200
actual_popen=runtime_module.subprocess.Popen
children=[]
def observed_popen(*args,**kwargs):
    child=actual_popen(*args,**kwargs)
    children.append(child)
    return child
runtime_module.subprocess.Popen=observed_popen
result={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':'synthetic workspace; real registered HTTP handlers and pinned restricted CLI control; no model or account request',
        'status':'NOT_COMPLETED','events':[]}
# Git above is provenance only; do not count it as a control subprocess.
children.clear()
def post(path,body,key):
    response=client.post('/api/v1/codex/'+path,json=body,headers={**headers,'Idempotency-Key':key})
    return response

def get(path):
    with app.state.database.connect() as connection: before=tuple(connection.iterdump())
    response=client.get('/api/v1/codex/'+path)
    with app.state.database.connect() as connection: assert tuple(connection.iterdump())==before
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    return response.json()
try:
    preparation=post('session-preparations',{'sandbox_root_id':'workspace_default','allowed_actions':[]},'actual-prepare')
    assert preparation.status_code==201
    original=preparation.json();result['preparation_ack']=original
    path='session-preparations/'+original['id']
    result['preparation_current']=get(path)
    assert original['validity']=='current' and children==[]
    decision=post(path+'/decision',{'expected_revision':1,'operation_sha256':original['operation_sha256'],'decision':'approve_once'},'actual-decision')
    assert decision.status_code==200
    result['decision_ack']=decision.json()
    approved=get(path)
    assert approved['status']=='approved' and approved['validity']=='current' and children==[]
    body={'sandbox_root_id':'workspace_default','consent_id':decision.json()['consent_id'],'allowed_actions':[]}
    started=time.monotonic();response=post('sessions',body,'actual-create');elapsed=time.monotonic()-started
    result['create_status']=response.status_code;result['create_seconds']=elapsed
    # These public handlers expose only strict views or safe error messages.
    result['create_response']=response.json()
    consumed=get(path);session=get('sessions/'+consumed['session_id'])
    result['consumed_preparation']=consumed;result['session_current']=session
    assert len(children)==1 and children[0].poll() is not None
    replay=post('sessions',body,'actual-create')
    assert replay.status_code==response.status_code and replay.content==response.content and len(children)==1
    result['original_response_replay_bytes_equal']=True
    second=create_app(settings);second.state.database.initialize()
    workspace=client.get('/api/v1/session').json()['workspace_id']
    assert second.state.codex_bootstrap_service.recover(workspace)==0
    second_client=TestClient(second,base_url=settings.origin);second_client.cookies.update(client.cookies)
    reread=second_client.get('/api/v1/codex/sessions/'+consumed['session_id'])
    assert reread.status_code==200 and reread.json()==session
    rereplay=second_client.post('/api/v1/codex/sessions',json=body,headers={**headers,'Idempotency-Key':'actual-create'})
    assert rereplay.status_code==response.status_code and rereplay.content==response.content and len(children)==1
    result['application_recreation_same_db_original_replay_bytes_equal']=True
    result['control_process_count']=len(children)
    result['control_exit_codes']=[child.returncode for child in children]
    result['pipes_closed']=all(child.stdin.closed and child.stdout.closed and child.stderr.closed for child in children)
    assert result['pipes_closed']
    assert session['capabilities']=={'approvals':False,'interrupt':False,'artifacts':False}
    if response.status_code==201:
        assert session['status']=='ready'
        result['status']='PASS_REAL_RESTRICTED_CONTROL'
    else:
        assert response.status_code==503 and session['status'] in {'failed','unknown'}
        result['status']='BLOCKED_REAL_RESTRICTED_CONTROL'
finally:
    runtime_module.subprocess.Popen=actual_popen
    (OUT/'actual.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'http':result.get('create_status'),'session':result.get('session_current',{}).get('status'),'control_count':result.get('control_process_count')}))
