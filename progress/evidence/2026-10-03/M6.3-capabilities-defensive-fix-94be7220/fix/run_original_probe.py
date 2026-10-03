"""Same independent probe bytes; remap only child source cwd and private tmp root."""
from pathlib import Path
import runpy,subprocess,sys,tempfile
root=sys.argv[2]
assert root in ['$HOME/.cache/learning-workbench-acceptance/m63-codex-capabilities-oct03','$HOME/.cache/learning-workbench-acceptance/m63-capability-contract-checks-oct03']
original_popen=subprocess.Popen
original_temp=tempfile.TemporaryDirectory
def scoped_popen(*args,**kwargs):
    assert kwargs['cwd']=='$HOME/.cache/learning-workbench-acceptance/m63-capabilities-independent-review-tree-oct03'
    kwargs['cwd']=root
    return original_popen(*args,**kwargs)
def scoped_temp(*args,**kwargs):
    assert kwargs['dir']=='$HOME/.cache/lw-cir'
    kwargs['dir']='$HOME/.cache/m63-capability-tmp'
    return original_temp(*args,**kwargs)
subprocess.Popen=scoped_popen
tempfile.TemporaryDirectory=scoped_temp
runpy.run_path(str(Path(__file__).with_name(sys.argv[1])),run_name='__main__')
