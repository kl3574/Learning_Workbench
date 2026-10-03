"""Owned synthetic SysV IPC resource only; cleanup always removes the segment."""
from pathlib import Path
import ctypes,json,os,subprocess,sys,tempfile
libc=ctypes.CDLL(None,use_errno=True);libc.shmat.restype=ctypes.c_void_p
identifier=libc.shmget(0,4096,0o1000|0o600)
assert identifier>=0
address=libc.shmat(identifier,None,0);assert address!=ctypes.c_void_p(-1).value
ctypes.memmove(address,b'SYNTHETIC_BEFORE\x00',17)
program=r'''
import ctypes,json,sys
from pathlib import Path
from services.api.app.infrastructure.codex_probe_isolation import restrict_probe
libc=ctypes.CDLL(None,use_errno=True);libc.shmat.restype=ctypes.c_void_p
restrict_probe(Path(sys.executable),Path(sys.argv[1]))
address=libc.shmat(int(sys.argv[2]),None,0)
out={'attached':address!=ctypes.c_void_p(-1).value,'errno':ctypes.get_errno()}
if out['attached']:
 out['read_synthetic']=ctypes.string_at(address,17)==b'SYNTHETIC_BEFORE\x00'
 ctypes.memmove(address,b'SYNTHETIC_AFTER\x00',16)
 libc.shmdt(ctypes.c_void_p(address))
print(json.dumps(out))
'''
try:
    with tempfile.TemporaryDirectory(prefix='sysv-',dir='$HOME/.cache/lw-cir') as td:
        run=subprocess.run([sys.executable,'-c',program,td,str(identifier)],capture_output=True,timeout=3,
            cwd='$HOME/.cache/learning-workbench-acceptance/m63-capabilities-independent-review-tree-oct03',
            env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},close_fds=True)
        print(json.dumps({'child_exit':run.returncode,'child':json.loads(run.stdout) if run.returncode==0 else None,
                          'parent_observed_synthetic_write':ctypes.string_at(address,16)==b'SYNTHETIC_AFTER\x00'}))
finally:
    libc.shmdt(ctypes.c_void_p(address));assert libc.shmctl(identifier,0,None)==0
