"""Own synthetic queue only. Probe kernel access, not actual CLI behavior."""
from pathlib import Path
import ctypes,json,os,subprocess,sys,tempfile,uuid
libc=ctypes.CDLL(None,use_errno=True)
name=('/lwcap_'+uuid.uuid4().hex).encode()
queue=libc.mq_open(name,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NONBLOCK,0o600,None)
if queue<0:
 print(json.dumps({'parent_queue_created':False,'errno':ctypes.get_errno()}));raise SystemExit(2)
program=r'''
import ctypes,json,os,sys
from pathlib import Path
from services.api.app.infrastructure.codex_probe_isolation import restrict_probe
libc=ctypes.CDLL(None,use_errno=True)
restrict_probe(Path(sys.executable),Path(sys.argv[1]))
queue=libc.mq_open(sys.argv[2].encode(),os.O_WRONLY|os.O_NONBLOCK)
out={'opened':queue>=0,'errno':ctypes.get_errno()}
if queue>=0:
 data=b'SYNTHETIC_MQ';out['sent']=libc.mq_send(queue,data,len(data),0)==0;libc.mq_close(queue)
print(json.dumps(out))
'''
try:
 with tempfile.TemporaryDirectory(dir='$HOME/.cache/m63-capability-tmp') as td:
  run=subprocess.run([sys.executable,'-c',program,td,name.decode()],cwd='$HOME/.cache/learning-workbench-acceptance/m63-codex-capabilities-oct03',env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,close_fds=True,timeout=3)
  buffer=ctypes.create_string_buffer(8192);count=libc.mq_receive(queue,buffer,8192,None)
  print(json.dumps({'parent_queue_created':True,'child_exit':run.returncode,'child':json.loads(run.stdout) if run.returncode==0 else None,'parent_received_synthetic':count==12 and buffer.raw[:count]==b'SYNTHETIC_MQ'}))
finally:
 libc.mq_close(queue);assert libc.mq_unlink(name)==0
