"""Actual kernel counterexamples: unnamed pairs must not address outside peers."""
import json
import ctypes
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest


@pytest.mark.parametrize('operation', ['sendto', 'sendmsg', 'sendmmsg'])
def test_pair_cannot_send_to_an_existing_named_socket_outside_broker(tmp_path, operation):
    broker = tmp_path / 'broker'
    broker.mkdir()
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    # Abstract UNIX names also bypass filesystem rules, so cover that scope.
    endpoint = '\0learning_capability_' + str(os.getpid()) + '_' + operation
    listener.bind(endpoint)
    listener.settimeout(0.1)
    program = r'''
import ctypes,errno,json,socket,sys
from pathlib import Path
from services.api.app.infrastructure.codex_probe_isolation import restrict_probe
broker,endpoint,operation=sys.argv[1:]
endpoint='\0'+endpoint
libc=ctypes.CDLL(None,use_errno=True)
restrict_probe(Path(sys.executable),Path(broker))
left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
left.send(b'internal')
assert right.recv(32)==b'internal'
payload=b'SYNTHETIC_DESTINATION'
result={'internal_pair':True,'denied':False}
try:
 if operation=='sendto':left.sendto(payload,endpoint)
 elif operation=='sendmsg':left.sendmsg([payload],[],0,endpoint)
 else:
  class Iov(ctypes.Structure):_fields_=[('base',ctypes.c_void_p),('size',ctypes.c_size_t)]
  class Header(ctypes.Structure):_fields_=[('name',ctypes.c_void_p),('name_len',ctypes.c_uint),('iov',ctypes.POINTER(Iov)),('iov_len',ctypes.c_size_t),('control',ctypes.c_void_p),('control_len',ctypes.c_size_t),('flags',ctypes.c_int)]
  class Many(ctypes.Structure):_fields_=[('header',Header),('length',ctypes.c_uint)]
  address=ctypes.create_string_buffer(b'\x01\x00'+endpoint.encode())
  body=ctypes.create_string_buffer(payload)
  iov=Iov(ctypes.cast(body,ctypes.c_void_p),len(payload))
  message=Many(Header(ctypes.cast(address,ctypes.c_void_p),len(endpoint.encode())+2,ctypes.pointer(iov),1,None,0,0),0)
  if libc.syscall(307,left.fileno(),ctypes.byref(message),1,0)<0:raise OSError(ctypes.get_errno(),'synthetic syscall failed')
except OSError as error:result['denied']=error.errno==errno.EPERM
left.close();right.close()
print(json.dumps(result))
'''
    try:
        run = subprocess.run([sys.executable, '-c', program, str(broker), endpoint[1:], operation],
            cwd=Path(__file__).parents[2], env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},
            close_fds=True, capture_output=True, timeout=3)
        assert run.returncode == 0, run.stderr.decode()[-1000:]
        result = json.loads(run.stdout)
        received = False
        try:
            received = listener.recv(64) == b'SYNTHETIC_DESTINATION'
        except socket.timeout:
            pass
        assert result == {'internal_pair':True,'denied':True}
        assert not received
    finally:
        listener.close()


def test_fifo_configuration_is_rejected_without_a_blocking_open(tmp_path):
    program = '''
from pathlib import Path
import os,sys
from services.api.app.infrastructure.codex_probe import LocalCodexProbe
from services.api.app.application.errors import ApiError
base=Path(sys.argv[1]);binary=base/'unused-binary';binary.write_bytes(b'synthetic')
home=base/'data'/'codex-broker'/'home';home.mkdir(parents=True,mode=0o700)
for path in [home.parent,home.parent.parent]:path.chmod(0o700)
os.mkfifo(home/'config.toml',0o600)
try:LocalCodexProbe(base/'data',binary).read()
except ApiError as error:
 assert error.code=='CODEX_BROKER_CONFIG_CHANGED'
 print('FIFO_REJECTED_WITHOUT_EXEC')
else:raise AssertionError('FIFO admitted')
'''
    run = subprocess.run([sys.executable, '-c', program, str(tmp_path)],
        cwd=Path(__file__).parents[2], env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},
        close_fds=True, capture_output=True, timeout=2)
    assert run.returncode == 0, run.stderr.decode()[-1000:]
    assert run.stdout == b'FIFO_REJECTED_WITHOUT_EXEC\n'


def test_sendto_checks_both_pointer_words_and_message_fd_apis_are_denied(tmp_path):
    program = r'''
import ctypes,errno,json,socket,sys
from pathlib import Path
from services.api.app.infrastructure.codex_probe_isolation import restrict_probe
libc=ctypes.CDLL(None,use_errno=True)
restrict_probe(Path(sys.executable),Path(sys.argv[1]))
left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
results=[]
for destination in [1,1<<32]:
 value=libc.syscall(44,left.fileno(),b'x',1,0,ctypes.c_void_p(destination),2)
 results.append(value==-1 and ctypes.get_errno()==errno.EPERM)
for call in [46,47,299,307]:
 value=libc.syscall(call,left.fileno(),None,0,0,None)
 results.append(value==-1 and ctypes.get_errno()==errno.EPERM)
print(json.dumps(results))
'''
    run = subprocess.run([sys.executable,'-c',program,str(tmp_path)],cwd=Path(__file__).parents[2],
        env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},close_fds=True,capture_output=True,timeout=3)
    assert run.returncode == 0, run.stderr.decode()[-1000:]
    assert json.loads(run.stdout) == [True] * 6


def test_sysv_shared_memory_cannot_read_or_change_an_existing_external_segment(tmp_path):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.shmat.restype = ctypes.c_void_p
    identifier = libc.shmget(0, 4096, 0o1000 | 0o600)
    assert identifier >= 0
    address = libc.shmat(identifier, None, 0)
    assert address != ctypes.c_void_p(-1).value
    original = b'SYNTHETIC_SHARED_BEFORE\0'
    ctypes.memmove(address, original, len(original))
    program = r'''
import ctypes,errno,json,sys
from pathlib import Path
from services.api.app.infrastructure.codex_probe_isolation import restrict_probe
libc=ctypes.CDLL(None,use_errno=True);libc.shmat.restype=ctypes.c_void_p
restrict_probe(Path(sys.executable),Path(sys.argv[1]))
address=libc.shmat(int(sys.argv[2]),None,0)
denied=address==ctypes.c_void_p(-1).value and ctypes.get_errno()==errno.EPERM
if not denied:
 ctypes.memmove(address,b'SYNTHETIC_SHARED_AFTER\0',23)
 libc.shmdt(ctypes.c_void_p(address))
print(json.dumps({'denied':denied}))
'''
    try:
        run = subprocess.run([sys.executable,'-c',program,str(tmp_path),str(identifier)],
            cwd=Path(__file__).parents[2],env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},
            close_fds=True,capture_output=True,timeout=3)
        assert run.returncode == 0, run.stderr.decode()[-1000:]
        assert (json.loads(run.stdout), ctypes.string_at(address, len(original))) == ({'denied':True}, original)
    finally:
        libc.shmdt(ctypes.c_void_p(address))
        assert libc.shmctl(identifier, 0, None) == 0
