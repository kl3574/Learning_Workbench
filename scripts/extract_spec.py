"""Extract normative code blocks from PRODUCT_DESIGN.md; refuse overwriting edits.
Usage: python scripts/extract_spec.py PRODUCT_DESIGN.md [destination]
This helper itself can be copied from appendix G; no network or credentials required.
"""
from pathlib import Path, PurePosixPath
import re, sys
PATTERN=re.compile(r'^<!-- BEGIN FILE: ([A-Za-z0-9_./-]+) -->\n~~~[a-zA-Z0-9_-]*\n(.*?)\n~~~\n<!-- END FILE -->',re.M|re.S)
def extract(spec:Path,destination:Path):
    text=spec.read_text(encoding='utf-8');root=destination.resolve();root.mkdir(parents=True,exist_ok=True)
    entries=PATTERN.findall(text)
    if not entries: raise ValueError('no embedded files found')
    seen=set();pending=[]
    for relative,body in entries:
        p=PurePosixPath(relative)
        if p.is_absolute() or '..' in p.parts or str(p)!=relative or relative in seen:
            raise ValueError(f'invalid or duplicate path: {relative}')
        seen.add(relative);target=root/relative
        if not target.resolve().is_relative_to(root): raise ValueError('symlink or path escape')
        data=(body+'\n').encode('utf-8')
        if target.exists() and target.read_bytes()!=data: raise ValueError(f'edited destination: {relative}')
        pending.append((target,data))
    for target,data in pending:
        target.parent.mkdir(parents=True,exist_ok=True)
        # Recheck parents after mkdir, do not follow pre-existing escaping symlinks.
        if not target.resolve().is_relative_to(root): raise ValueError('path changed')
        if not target.exists(): target.write_bytes(data)
    return [str(x.relative_to(root)) for x,_ in pending]
if __name__=='__main__':
    spec=Path(sys.argv[1] if len(sys.argv)>1 else 'PRODUCT_DESIGN.md')
    destination=Path(sys.argv[2]) if len(sys.argv)>2 else spec.parent
    for entry in extract(spec,destination): print(entry)
