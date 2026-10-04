"""Exact reviewer probe bytes; only isolated source cwd and temp root remapped."""
from pathlib import Path
import runpy,subprocess,tempfile
root='$HOME/.cache/learning-workbench-acceptance/m63-codex-capabilities-oct03'
original_run=subprocess.run
original_temp=tempfile.TemporaryDirectory
def scoped_run(*args,**kwargs):
    assert kwargs['cwd']=='$HOME/.cache/learning-workbench-acceptance/m63-capabilities-independent-review-tree-oct03'
    kwargs['cwd']=root
    return original_run(*args,**kwargs)
def scoped_temp(*args,**kwargs):
    assert kwargs['dir']=='$HOME/.cache/lw-cir'
    kwargs['dir']='$HOME/.cache/m63-capability-tmp'
    return original_temp(*args,**kwargs)
subprocess.run=scoped_run
tempfile.TemporaryDirectory=scoped_temp
runpy.run_path(str(Path(__file__).with_name('reviewer-ipc-probe.py')),run_name='__main__')
