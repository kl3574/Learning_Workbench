"""Independent local synthetic IPC-only probe; no network or account/CLI access."""
from pathlib import Path
import json,os,socket,subprocess,sys,tempfile

program=r'''
import json,os,socket,sys
from pathlib import Path
from services.api.app.infrastructure.codex_probe_isolation import restrict_probe
broker,target,outside=sys.argv[1:]
restrict_probe(Path(sys.executable),Path(broker))
out={'outside_read_denied':False,'network_socket_denied':False}
try:Path(outside).read_bytes()
except PermissionError:out['outside_read_denied']=True
try:socket.socket(socket.AF_INET,socket.SOCK_STREAM)
except PermissionError:out['network_socket_denied']=True
left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
try:
 out['sent']=left.sendto(b'SYNTHETIC_IPC_ONLY',target)
except OSError as exc:out['send_errno']=exc.errno
left.close();right.close()
print(json.dumps(out),flush=True)
'''
with tempfile.TemporaryDirectory(prefix='ipc-',dir='$HOME/.cache/lw-cir') as td:
    base=Path(td);broker=base/'broker';broker.mkdir();outside=base/'outside';outside.write_text('SYNTHETIC_OUTSIDE')
    endpoint=str(base/'target.sock')
    listener=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);listener.bind(endpoint);listener.settimeout(0.5)
    run=subprocess.run([sys.executable,'-c',program,str(broker),endpoint,str(outside)],capture_output=True,timeout=3,
                       cwd='$HOME/.cache/learning-workbench-acceptance/m63-capabilities-independent-review-tree-oct03',
                       env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},close_fds=True)
    result={'child_exit':run.returncode,'child':json.loads(run.stdout) if run.returncode==0 else None,'received_synthetic':False}
    try:result['received_synthetic']=listener.recv(128)==b'SYNTHETIC_IPC_ONLY'
    except socket.timeout:pass
    listener.close()
    print(json.dumps(result))
