"""Explicit group-only native fixture; no production factory discovers its proof.

Only this selected test factory registers complete-byte proof for its own actual
loopback address. It seeds original synthetic Content targets, never draft refs.
No request bodies, headers, credentials, profiles or sessions enter observations.
"""

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from typing import Any

from fastapi import FastAPI

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.provider_budget import RequestPreparer
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.main import create_app
from tests.authoring_native_fixture import PAYLOAD as WORKED_EXAMPLE
from tests.provider_protocol_fixture import MODEL, complete_byte_count, local_provider, test_preparer

TOPIC = '原创合成组合创作'
OBJECTIVES = ['区分草稿结构、数值复算与教学审核。']


def targets():
    concept = dm.Concept(id='concept_group_native', revision=1, title='原创合成倍数概念')
    body = '这是供显式选择的已有小节目标；不自动加入生成来源。\n'.encode()
    block = dm.ContentBlock(id='block_group_native_target', revision=1, kind='text', title='原始合成目标正文',
        body_path='content/group-native-target.md', body_sha256=sha256_bytes(body))
    lesson = dm.Lesson(id='lesson_group_native_target', revision=1, title='原创合成已有小节',
        objectives=['识别倍数关系'], block_refs=[reference(block)])
    course = dm.Course(id='course_group_native_target', revision=1, title='原创合成组目标课程', audience='合成验收',
        lesson_refs=[reference(lesson)], concept_refs=[reference(concept)])
    return concept, lesson, [concept, block, lesson, course], {block.body_path: body}


def payload(scenario: str) -> dict[str, Any]:
    concept, _, _, _ = targets()
    plan: dict[str, Any] = {'version': 'authoring-content-plan-v1', 'output_kind': scenario, 'topic': TOPIC,
        'prerequisites': [], 'objectives': OBJECTIVES, 'proof_policy': 'full', 'entries': []}
    if scenario == 'lesson':
        blocks: list[dict[str, Any]] = [
            {'member_key': 'definition', 'depends_on_keys': [], 'payload': {
                'version': 'content-block-candidate-v1', 'kind': 'definition', 'title': '原创合成倍数定义',
                'body_markdown': '设 $x$ 为实数，定义倍数函数。\n\n$$f(x)=2x.$$\n\n定义不是计算验证或教学审核。',
                'symbols': [], 'declared_source_refs': []}},
            {'member_key': 'example', 'depends_on_keys': ['definition'], 'payload': WORKED_EXAMPLE},
        ]
        plan['entries'] = [{'member_key': block['member_key'], 'entity': 'block', 'kind': block['payload']['kind'],
            'title': block['payload']['title'], 'objective_indexes': [0], 'prerequisite_indexes': [],
            'depends_on_keys': block['depends_on_keys']} for block in blocks]
        draft: dict[str, Any] = {'output_kind': scenario, 'title': '原创合成教材组草稿', 'blocks': blocks}
    elif scenario == 'practice_set':
        question = {'member_key': 'question_double', 'kind': 'numeric', 'stem_markdown': '当 $x=9$ 时，求 $2x$。',
            'choices': [], 'concept_refs': [reference(concept).model_dump()], 'skill': 'compute',
            'exposure_family_key': 'family_group_native', 'max_score': 1.0, 'input_instructions': '输入数值',
            'declared_source_refs': [], 'depends_on_keys': []}
        answer = {'question_key': question['member_key'], 'grading_kind': 'numeric_tolerance',
            'accepted_answers': ['18', '18.0'], 'absolute_tolerance': 0.0, 'relative_tolerance': 0.0,
            'unit': None, 'domain_assumptions': [], 'solution_markdown': '私有合成解答：$2\\times 9=18$，尚未审查。',
            'rubric_markdown': '保留两种允许答案表示；未经评分语义审核。', 'symbols': WORKED_EXAMPLE['symbols'],
            'numeric_plan': WORKED_EXAMPLE['numeric_plan']}
        plan['entries'] = [{'member_key': question['member_key'], 'entity': 'question', 'kind': 'numeric',
            'objective_indexes': [0], 'prerequisite_indexes': [], 'depends_on_keys': []}]
        draft = {'output_kind': scenario, 'title': '原创合成习题组草稿', 'questions': [question], 'solutions': [answer]}
    else:
        raise ValueError('Unknown closed group native scenario')
    return {'version': 'authoring-group-generated-v1', 'content_plan': plan, 'draft': draft}


def create_test_app() -> FastAPI:
    settings = Settings.from_env()
    scenario = os.environ.get('AUTHORING_NATIVE_SCENARIO')
    if scenario not in {'lesson', 'practice_set'}:
        raise ValueError('Select a closed group native test scenario')
    answer = canonical_bytes(payload(scenario)).decode()
    preparer = RequestPreparer()
    application = create_app(settings, request_preparer=preparer)
    original_lifespan = application.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with local_provider(text=answer) as provider:
            preparer.registry = test_preparer(provider.base_url).registry
            async with original_lifespan(app) as state:
                _, _, objects, bodies = targets()
                ContentService(app.state.database).publish(app.state.database.workspace_id(), objects, bodies)
                path = settings.data_dir / 'authoring-native-control.json'
                pending = path.with_suffix('.pending')
                stopped = asyncio.Event()

                def observe():
                    valid, invalid = [], 0
                    for body in provider.requests:
                        try:
                            complete_byte_count(body)
                        except (ValueError, TypeError, KeyError):
                            invalid += 1
                        else:
                            valid.append(hashlib.sha256(body).hexdigest())
                    value = {'version': 'authoring-group-native-fixture-v1', 'scenario': scenario,
                        'test_only': True, 'proof_registered': True, 'adapter': 'compatible_chat', 'model': MODEL,
                        'base_url': provider.base_url, 'answer_markdown': answer,
                        'received_request_count': len(provider.requests), 'validated_request_count': len(valid),
                        'invalid_request_count': invalid, 'request_body_sha256': valid}
                    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
                    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(raw)
                    os.replace(pending, path)

                async def monitor():
                    while not stopped.is_set():
                        try:
                            await asyncio.wait_for(stopped.wait(), 0.05)
                        except TimeoutError:
                            observe()

                observe()
                monitoring = asyncio.create_task(monitor())
                try:
                    yield state
                finally:
                    stopped.set()
                    await monitoring
                    observe()

    application.router.lifespan_context = lifespan
    return application
