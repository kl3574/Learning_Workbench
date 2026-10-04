"""Read-only GitHub artifact transfer, exact approved JSON members only."""
from pathlib import Path, PurePosixPath
import subprocess, selectors, time, hashlib, json, io, zipfile, datetime, stat
E=Path(__file__).resolve().parent
EXPECTED='69029bc1ab355efdbb6e0fdb8a86204c59cea71a'
sha=lambda b:hashlib.sha256(b).hexdigest()
def bounded_get(endpoint,limit):
 p=subprocess.Popen(['gh','api','--method','GET',endpoint],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ,'out');sel.register(p.stderr,selectors.EVENT_READ,'err');out=bytearray();err=bytearray();start=time.monotonic()
 try:
  while sel.get_map():
   if time.monotonic()-start>45:raise RuntimeError('bounded API timeout')
   for key,_ in sel.select(1):
    block=key.fileobj.read1(65536)
    if not block:sel.unregister(key.fileobj);continue
    dest=out if key.data=='out' else err;dest.extend(block)
    if len(dest)>(limit if key.data=='out' else 65536):raise RuntimeError('bounded API byte budget exceeded')
  code=p.wait(timeout=5)
  if code:raise RuntimeError(f'API exit {code}; stderr sha256 {sha(err)}')
  return bytes(out),bytes(err)
 finally:
  sel.close()
  if p.poll() is None:p.kill();p.wait(timeout=5)
