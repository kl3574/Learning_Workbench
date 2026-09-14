"""Original assessment packages; private answers remain explicitly unreviewed."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import Literal
import zipfile

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from packages.contracts.validation import PublishedModel
from services.api.app.infrastructure.content_repository import reference
from tests.practice_fixtures import PracticeFixture, practice_fixture


@dataclass(frozen=True)
class AssessmentFixture(PracticeFixture):
    assessment: dm.AssessmentBlueprint

    @property
    def public_objects(self) -> list[PublishedModel]:
        return [*super().public_objects, self.assessment]


def assessment_fixture(prefix: str = 'assessment', *, profile: Literal['learner', 'author'] = 'author',
                       revision: int = 1, time_limit_seconds: int | None = None) -> AssessmentFixture:
    original = practice_fixture(prefix, profile=profile, revision=revision)
    assessment = dm.AssessmentBlueprint(id=f'assessment_{prefix}', revision=revision,
        title='数量关系参考测验：未审核内容的作答记录',
        question_refs=[reference(q) for q in original.questions],
        allowed_modes=['independent', 'open_book', 'assisted'], time_limit_seconds=time_limit_seconds)
    with zipfile.ZipFile(BytesIO(original.archive)) as archive:
        payloads = {name: archive.read(name) for name in archive.namelist() if name != 'manifest.json'}
    payloads[f'assessments/{assessment.id}.r{revision}.json'] = canonical_bytes(assessment)
    manifest = dm.Manifest(package_id=f'package_assessment_{prefix}_{profile}_r{revision}', profile=profile,
        created_at='2026-09-14T00:00:00Z', files=[dm.FileEntry(path=path, sha256=sha256(value).hexdigest(), size=len(value),
            media_type='text/markdown' if path.endswith('.md') else 'application/json',
            visibility='author_private' if path.startswith('private/') else 'learner') for path, value in sorted(payloads.items())])
    payloads['manifest.json'] = canonical_bytes(manifest)
    output = BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for path, value in sorted(payloads.items()):
            info = zipfile.ZipInfo(path, date_time=(2026, 9, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, value)
    return AssessmentFixture(archive=output.getvalue(), course=original.course, lesson=original.lesson,
        block=original.block, concept=original.concept, practice=original.practice, questions=original.questions,
        solutions=original.solutions, bodies=original.bodies, assessment=assessment)
