"""Verify public bytes and optionally replay parameterized private path substitutions."""
import argparse
import ast
import re
import hashlib
import json
from pathlib import Path, PurePosixPath


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


RULES = {'652caa2462ac43fe4bd6ab45f76847cc0684a7ae8c7019dd8be49604fb1051b3': {'kind': 'tutor_fixture_secret', 'value_sha256': '269bbce5a1df4a125b006325a747062bb80335326dd98380ebbfbc6f6967360b'}, '090d819dcbd5720a4e487fd1b8cfe4b123e68e633b619e580bbada8de3b11f44': {'kind': 'loopback_fixture_secret', 'value_sha256': '9c64e7f1d4d550d68ad1b7169dd73f7f108fa9f71562b7d04a05aa73e860e346'}}
FIELD = re.compile(rb"\bsecret=(?P<quote>['\"])(?P<value>[^'\"\r\n]+)(?P=quote)")


def redaction_spans(data):
    matches = [m for m in FIELD.finditer(data) if hashlib.sha256(m.group()).hexdigest() in RULES]
    if not matches:
        return []
    tree = ast.parse(data.decode('utf-8'))
    lines = data.splitlines(keepends=True)
    def offset(line, column):
        return sum(len(v) for v in lines[:line - 1]) + column
    allowed = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'ProviderSecretWrite':
            for field in node.keywords:
                if field.arg == 'secret' and isinstance(field.value, ast.Constant) and isinstance(field.value.value, str):
                    allowed.add((offset(field.lineno, field.col_offset), offset(field.end_lineno, field.end_col_offset)))
    found = []
    for match in matches:
        assert match.span() in allowed, 'secret literal is outside exact ProviderSecretWrite keyword'
        digest = hashlib.sha256(match.group()).hexdigest()
        rule = RULES[digest]
        assert hashlib.sha256(match.group('value')).hexdigest() == rule['value_sha256']
        start, end = match.span('value')
        found.append({'start': start, 'end': end, 'kind': rule['kind'],
                      'field_sha256': digest, 'value_sha256': rule['value_sha256']})
    return found


def transform(data, raw_home, ci_home, expected_spans=None):
    found = redaction_spans(data)
    if expected_spans is not None:
        assert found == expected_spans, 'exact original field/context/spans differ'
    counts = {rule['kind']: 0 for rule in RULES.values()}
    for item in reversed(found):
        counts[item['kind']] += 1
        data = data[:item['start']] + b'<SYNTHETIC>' + data[item['end']:]
    rules = [
        ('local_home_slash', (raw_home.rstrip('/') + '/').encode(), b'<LOCAL_HOME>/'),
        ('local_home_bare', raw_home.rstrip('/').encode(), b'<LOCAL_HOME>'),
        ('ci_home_slash', (ci_home.rstrip('/') + '/').encode(), b'<CI_HOME>/'),
        ('ci_home_bare', ci_home.rstrip('/').encode(), b'<CI_HOME>'),
        ('pytest_user_root', b'/tmp/pytest-of-' + Path(raw_home).name.encode(), b'<PYTEST_ROOT>'),
    ]
    for name, old, new in rules:
        counts[name] = data.count(old)
        data = data.replace(old, new)
    return data, counts, found


def safe_path(base, relative):
    path = PurePosixPath(relative)
    assert not path.is_absolute() and '..' not in path.parts and path.parts
    result = base / relative
    assert result.resolve().is_relative_to(base.resolve())
    return result


def checked(path, size, digest):
    data = path.read_bytes()
    assert len(data) == size and hashlib.sha256(data).hexdigest() == digest, str(path)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-base', type=Path)
    parser.add_argument('--raw-home')
    parser.add_argument('--ci-home')
    args = parser.parse_args()
    if args.raw_base and (not args.raw_home or not args.ci_home):
        parser.error('--raw-home and --ci-home are required for raw replay')
    if args.raw_base:
        assert Path(args.raw_home).is_absolute() and Path(args.ci_home).is_absolute()
        assert args.raw_home.rstrip('/') and args.ci_home.rstrip('/')
        assert args.raw_home.rstrip('/') != args.ci_home.rstrip('/')
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'manifest.json').read_bytes())
    aggregate = {'files': manifest['files'], 'generated_files': manifest['generated_files']}
    assert hashlib.sha256(canonical(aggregate)).hexdigest() == manifest['aggregate_sha256']
    expected = {'manifest.json'}
    aliases = set()
    for item in manifest['files']:
        alias = (item['raw_cache'], item['raw_path'])
        assert alias not in aliases
        aliases.add(alias)
        expected.add(item['public_path'])
        actual = checked(safe_path(root, item['public_path']), item['public_bytes'], item['public_sha256'])
        if args.raw_base:
            raw = checked(safe_path(args.raw_base, '/'.join(alias)), item['raw_bytes'], item['raw_sha256'])
            transformed, counts, _ = transform(raw, args.raw_home, args.ci_home, item["redaction_spans"])
            assert transformed == actual and counts == item['transformation_counts']
            assert item['transformed'] == (raw != actual)
    for item in manifest['generated_files']:
        assert item['path'] not in expected
        expected.add(item['path'])
        checked(safe_path(root, item['path']), item['bytes'], item['sha256'])
    actual_paths = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual_paths == expected, 'unexpected/missing public files'
    print(f'PASS: {len(aliases)} raw aliases; {len(expected)} public files; aggregate verified' +
          ('; raw hashes and exact AST-validated synthetic literal spans and ordered path transformations replayed' if args.raw_base else ''))


if __name__ == '__main__':
    main()
