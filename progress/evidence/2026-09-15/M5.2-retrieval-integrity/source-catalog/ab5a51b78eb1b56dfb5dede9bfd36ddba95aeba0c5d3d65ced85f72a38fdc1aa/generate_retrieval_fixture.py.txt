"""Derive the frozen M5.2 fixture solely from PRODUCT_DESIGN.md appendix F.1.

This constructs hash-valid public models and gold refs, not database publication,
tokenization, retrieval, content review or measured Recall. Existing edits survive.
"""
# Imports below follow repo-root bootstrapping for standalone CLI execution.
# ruff: noqa: E402

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import sys
from typing import Literal, TypedDict

from pydantic import Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, strict_json

HEADING = '## F.1 M5.2 原创冻结词法基准 lexical-gold-v1'
_FENCE = re.compile(r'^```json\n(.*?)\n```$', re.M | re.S)


class _Block(dm.StrictModel):
    block_id: dm.Id
    kind: str
    title: str
    body_markdown: str
    body_utf8_sha256: dm.Sha256


class _Case(dm.StrictModel):
    case_id: str
    suite: Literal['literal_positive_recall', 'literal_no_result']
    query: str
    expected_block_ids: list[dm.Id]
    relevance_reason: str
    categories: list[str]


class _Definition(dm.StrictModel):
    corpus_version: Literal['m52-original-lexical-v1']
    status: Literal['SPEC_FIXTURE_NOT_EXECUTED']
    index_field: Literal['body_markdown']
    blocks: list[_Block] = Field(min_length=30, max_length=30)
    cases: list[_Case] = Field(min_length=42, max_length=42)


@dataclass(frozen=True)
class FixtureBuild:
    objects: tuple[dm.ContentBlock | dm.Lesson | dm.Course, ...]
    bodies: dict[str, bytes]
    payloads: dict[str, bytes]


class _PayloadRecord(TypedDict):
    path: str
    size: int
    sha256: str


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reference(value: dm.ContentBlock | dm.Lesson | dm.Course) -> dm.ContentRef:
    return dm.ContentRef(entity=value.entity, id=value.id, revision=value.revision, sha256=metadata_sha256(value))


def _definition(spec: bytes) -> tuple[_Definition, bytes]:
    text = spec.decode('utf-8')
    headings = [match for match in re.finditer(r'^' + re.escape(HEADING) + r'$', text, re.M)]
    if len(headings) != 1:
        raise ValueError('Expected one F.1 fixture heading.')
    following = text[headings[0].end():]
    boundary = re.search(r'^#{1,2} ', following, re.M)
    section = following[:boundary.start()] if boundary else following
    fences = _FENCE.findall(section)
    if len(fences) != 1:
        raise ValueError('Expected one F.1 JSON fence.')
    raw = fences[0].encode('utf-8')
    definition = _Definition.model_validate(strict_json(raw))
    ids = [f'm52_block_{number:02d}' for number in range(1, 31)]
    if [block.block_id for block in definition.blocks] != ids:
        raise ValueError('Frozen fixture block identities or order differ.')
    if [case.case_id for case in definition.cases] != [f'q{number:02d}' for number in range(1, 43)]:
        raise ValueError('Frozen fixture case identities or order differ.')
    for position, case in enumerate(definition.cases):
        if (len(case.expected_block_ids) != len(set(case.expected_block_ids))
                or set(case.expected_block_ids) - set(ids)
                or (position < 38) != bool(case.expected_block_ids)
                or case.suite != ('literal_positive_recall' if position < 38 else 'literal_no_result')
                or not 1 <= len(case.query) <= 512 or not case.query.strip()
                or not case.relevance_reason.strip() or not case.categories):
            raise ValueError('Invalid frozen gold relation.')
        case.query.encode('utf-8')
    return definition, raw


def build_fixture(spec: Path = ROOT / 'PRODUCT_DESIGN.md') -> FixtureBuild:
    """Build deterministic models and bytes without touching a destination or DB."""
    source = spec.read_bytes()
    definition, raw_gold = _definition(source)
    bodies: dict[str, bytes] = {}
    payloads: dict[str, bytes] = {}
    blocks: list[dm.ContentBlock] = []
    for item in definition.blocks:
        body = item.body_markdown.encode('utf-8')
        if _sha(body) != item.body_utf8_sha256 or b'\r' in body or body.endswith(b'\n'):
            raise ValueError('Frozen fixture body bytes or hash differ.')
        block = dm.ContentBlock.model_validate({
            'id': item.block_id, 'revision': 1, 'schema_version': '3.0.0',
            'kind': item.kind, 'title': item.title, 'body_path': f'content/{item.block_id}.md',
            'body_sha256': item.body_utf8_sha256, 'concepts': [], 'citations': [], 'depends_on': [],
        })
        blocks.append(block)
        bodies[block.body_path] = body
        payloads[block.body_path] = body
        payloads[f'blocks/{block.id}.r1.json'] = canonical_bytes(block)
    lesson = dm.Lesson(id='m52_lexical_lesson', revision=1, title='原创词法基准小节',
        objectives=[], prerequisite_ids=[], proof_policy='full', block_refs=[_reference(block) for block in blocks])
    course = dm.Course(id='m52_lexical_course', revision=1, title='原创词法基准课程',
        language='zh-CN', audience='工程验收未审材料', difficulty='beginner', objectives=[],
        concept_refs=[], sections=[], lesson_refs=[_reference(lesson)])
    payloads[f'lessons/{lesson.id}.r1.json'] = canonical_bytes(lesson)
    payloads['course.json'] = canonical_bytes(course)
    by_id = {block.id: _reference(block) for block in blocks}
    course_ref = _reference(course)
    cases = [{**case.model_dump(mode='json'), 'scope_refs': [course_ref.model_dump(mode='json')], 'limit': 5,
        'expected_refs': [by_id[identifier].model_dump(mode='json') for identifier in case.expected_block_ids]}
        for case in definition.cases]
    payloads['gold.json'] = canonical_bytes({'corpus_version': definition.corpus_version,
        'status': definition.status, 'cases': cases})
    inventory: list[_PayloadRecord] = [
        {'path': path, 'size': len(data), 'sha256': _sha(data)} for path, data in sorted(payloads.items())
    ]
    aggregate = _sha(b''.join((item['path'] + '\0' + item['sha256'] + '\n').encode() for item in inventory))
    payloads['passport.json'] = canonical_bytes({
        'format': 'retrieval-fixture-passport-v1', 'fixture_only': True,
        'source': {'file': 'PRODUCT_DESIGN.md', 'spec_sha256': _sha(source), 'section': HEADING,
                   'json_sha256': _sha(raw_gold), 'corpus_version': definition.corpus_version},
        'scope_refs': [course_ref.model_dump(mode='json')], 'lesson_ref': _reference(lesson).model_dump(mode='json'),
        'blocks': [{'ref': by_id[block.id].model_dump(mode='json'), 'body_path': block.body_path,
                    'body_sha256': block.body_sha256, 'body_bytes': len(bodies[block.body_path])} for block in blocks],
        'execution': {'content_published': False, 'retrieval_executed': False, 'recall_measured': False},
        'material_review': 'unreviewed', 'provenance_when_published_without_snapshot': 'unresolved',
        'evaluation': {'positive_cases': 38, 'no_result_cases': 4, 'limit': 5, 'metric': 'macro Recall@5',
                       'proposed_threshold': 0.90, 'results': None},
        'payloads': inventory, 'payload_aggregate_sha256': aggregate,
        'aggregate_algorithm': 'SHA256 of sorted relative path + NUL + lowercase ASCII file SHA256 + LF; passport excluded.',
    })
    return FixtureBuild(objects=(*blocks, lesson, course), bodies=bodies, payloads=payloads)


def generate(spec: Path, destination: Path, *, check: bool = False) -> tuple[Path, ...]:
    """Preflight every file; never overwrite edits, follow symlinks or delete extras."""
    payloads = build_fixture(spec).payloads
    destination = destination.absolute()
    targets = tuple(destination / relative for relative in sorted(payloads))
    for target in targets:
        if any(parent.is_symlink() for parent in (target, *target.parents)):
            raise ValueError('Refusing a symlink fixture destination.')
        if target.exists() and (not target.is_file() or target.read_bytes() != payloads[str(target.relative_to(destination))]):
            raise ValueError('Refusing an edited destination fixture.')
        if check and not target.exists():
            raise ValueError('Generated fixture is missing.')
    if destination.exists():
        unexpected = [path for path in destination.rglob('*') if (path.is_file() or path.is_symlink()) and path not in targets]
        if unexpected:
            raise ValueError('Refusing an edited destination with extra files.')
    if not check:
        for target in targets:
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(payloads[str(target.relative_to(destination))])
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = generate(ROOT / 'PRODUCT_DESIGN.md', ROOT / 'fixtures/synthetic/retrieval-m52', check=args.check)
    print(f'{"Verified" if args.check else "Generated"} {len(files)} frozen fixture files; retrieval and Recall NOT_RUN.')


if __name__ == '__main__':
    main()
