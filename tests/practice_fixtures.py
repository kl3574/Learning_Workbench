"""Original synthetic practice packages; no approval or external content claims."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import Literal
import zipfile

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from packages.contracts.validation import PublishedModel
from services.api.app.infrastructure.content_repository import reference


@dataclass(frozen=True)
class PracticeFixture:
    archive: bytes
    course: dm.Course
    lesson: dm.Lesson
    block: dm.ContentBlock
    concept: dm.Concept
    practice: dm.PracticeSet
    questions: tuple[dm.QuestionPublic, ...]
    solutions: tuple[dm.SolutionPrivate, ...]
    bodies: dict[str, bytes]

    @property
    def public_objects(self) -> list[PublishedModel]:
        return [self.concept, self.block, self.lesson, *self.questions, self.practice, self.course]


def practice_fixture(prefix: str = 'practice', *, profile: Literal['learner', 'author'] = 'author', revision: int = 1) -> PracticeFixture:
    if not prefix.isascii() or not prefix.isalpha() or revision not in {1, 2}:
        raise ValueError('Use an ASCII alphabetic prefix and revision 1 or 2')
    concept = dm.Concept(id=f'concept_{prefix}', revision=revision, title='数量关系与基本运算', skill_dimensions=['recall', 'compute', 'derive'])
    body = ('# 数量关系与基本运算\n\n本材料是原创软件验收样例，尚未接受独立内容审校。\n\n'
            '先辨认运算、变量与单位，再写出计算步骤。加法可以交换次序；路程除以时间得到速率；矩形面积由两条边长相乘得到。\n\n'
            '使用练习提示和参考解答会留下帮助与暴露记录，练习不等于独立测试。\n').encode()
    block = dm.ContentBlock(id=f'block_{prefix}', revision=revision, kind='text', title='数量、步骤与单位',
        body_path=f'content/block_{prefix}.r{revision}.md', body_sha256=sha256(body).hexdigest(), concepts=[concept.id])
    lesson = dm.Lesson(id=f'lesson_{prefix}', revision=revision, title='数量关系与基本运算：参考练习', objectives=['保留作答、核对单位和帮助记录'], block_refs=[reference(block)])
    specifications = [
        ('single_choice', '选择 $2+3$ 的结果。', '选择一个选项；练习尚未评分。', 'recall', 'choice_exact', ['choice_five'], None, '$2+3=5$，对应选项“5”。'),
        ('text_blank', '等式 $a+b=b+a$ 表达加法的哪一种性质？', '填写性质的中文名称。', 'recall', 'text_normalized', ['交换律', '加法交换律'], None, '该等式表达加法交换律。'),
        ('numeric', r'路程为 $12\,\mathrm{m}$，时间为 $3\,\mathrm{s}$，求速率。', '填写速率数值，单位为 m/s。', 'compute', 'numeric_tolerance', ['4'], 'm/s', r'速率为 $12/3=4\,\mathrm{m/s}$。'),
        ('calculation', r'矩形两条边长分别为 $2\,\mathrm{m}$ 和 $3\,\mathrm{m}$，求面积并写步骤。', '填写面积数值和推导，单位为 m²。', 'compute', 'numeric_tolerance', ['6'], 'm²', r'面积为 $2\times3=6\,\mathrm{m}^2$；还需独立检查步骤。'),
        ('expression', '已知实变量函数 $f(x)=x^2$，写出其导函数。', '填写表达式，并在步骤中说明适用范围。', 'derive', 'symbolic_review', ['2*x'], None, r'在实数域上，$f\prime(x)=2x$；表达式等价与推导仍需审阅。'),
    ]
    questions, solutions = [], []
    for index, (kind, stem, instructions, skill, grading, answers, unit, explanation) in enumerate(specifications):
        question = dm.QuestionPublic(id=f'question_{prefix}_{index}', revision=revision, kind=kind,
            stem_markdown=stem + ('\n\n第二修订：请重新核对条件。' if revision == 2 else ''),
            choices=[dm.Choice(id='choice_four', text_markdown='4'), dm.Choice(id='choice_five', text_markdown='5')] if kind == 'single_choice' else [],
            concept_ids=[concept.id], skill=skill, exposure_group=f'exposure_{prefix}_{index}', max_score=1.0, input_instructions=instructions)
        questions.append(question)
        solutions.append(dm.SolutionPrivate(id=f'solution_{prefix}_{index}', revision=revision, question_ref=reference(question),
            grading_kind=grading, accepted_answers=answers, unit=unit, solution_markdown=explanation,
            rubric_markdown='原创验收样例；未经正常审核不得用于真实学习者认证评分。', review_status='needs_review'))
    practice = dm.PracticeSet(id=f'practice_{prefix}', revision=revision, title='五类参考练习：作答与帮助记录',
        lesson_ref=reference(lesson), question_refs=[reference(question) for question in questions])
    course = dm.Course(id=f'course_{prefix}', revision=revision, title=f'原创练习验收教材 {prefix}', audience='软件验收用合成材料',
        lesson_refs=[reference(lesson)], concept_refs=[reference(concept)],
        sections=[dm.CourseSection(id=f'section_{prefix}', title='第一章：数量关系', lesson_ids=[lesson.id])])
    payloads = {'course.json': canonical_bytes(course), 'concepts.json': canonical_bytes([concept.model_dump(mode='json')]),
        'symbols.json': canonical_bytes([]), 'sources/citations.json': canonical_bytes([]), block.body_path: body,
        f'blocks/{block.id}.r{revision}.json': canonical_bytes(block), f'lessons/{lesson.id}.r{revision}.json': canonical_bytes(lesson),
        f'practice/{practice.id}.r{revision}.json': canonical_bytes(practice),
        'questions/public.jsonl': b'\n'.join(canonical_bytes(question) for question in questions) + b'\n'}
    if profile == 'author':
        payloads['private/solutions.jsonl'] = b'\n'.join(canonical_bytes(solution) for solution in solutions) + b'\n'
    manifest = dm.Manifest(package_id=f'package_{prefix}_{profile}_r{revision}', profile=profile, created_at='2026-09-14T00:00:00Z',
        files=[dm.FileEntry(path=path, sha256=sha256(value).hexdigest(), size=len(value), media_type='text/markdown' if path.endswith('.md') else 'application/json',
                           visibility='author_private' if path.startswith('private/') else 'learner') for path, value in sorted(payloads.items())])
    payloads['manifest.json'] = canonical_bytes(manifest)
    archive = BytesIO()
    with zipfile.ZipFile(archive, 'w') as output:
        for path, value in sorted(payloads.items()):
            entry = zipfile.ZipInfo(path, date_time=(2026, 9, 14, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(entry, value)
    return PracticeFixture(archive.getvalue(), course, lesson, block, concept, practice, tuple(questions), tuple(solutions), {block.body_path: body})
