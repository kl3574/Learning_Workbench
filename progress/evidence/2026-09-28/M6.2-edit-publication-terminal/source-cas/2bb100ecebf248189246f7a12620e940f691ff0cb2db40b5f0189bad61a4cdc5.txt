"""Same-transaction publication prerequisites; no publication or state mutation."""
import sqlite3

from packages.contracts.canonical import canonical_bytes, metadata_sha256
from ..authoring_dto import NumericPlan, WorkedExamplePayload
from ..authoring_group_dto import AuthoringGroupNumericCheckView, AuthoringDraftMemberRef
from ..import_dto import BlockDraftPayload
from ..infrastructure.review_repository import validated
from ..infrastructure.security import SessionIdentity
from .authoring_group_validation import member_ref
from .errors import ApiError
from .publication_admission_models import DraftPublishWrite, PublicationAdmission
from .review_history_models import ReviewDecisionRecord, ReviewMachineRecord
from .review_material_models import CheckedReviewMaterial, ImportReviewMaterial, SingleReviewMaterial, GroupReviewMaterial, EditReviewMaterial
from .review_numeric_models import NumericReviewCheck
from .review_service import ReviewService


def blocked(code: str, message: str) -> ApiError:
    return ApiError(409, code, message)


class PublicationAdmissionService:
    def __init__(self, reviews: ReviewService):
        self.reviews = reviews

    @staticmethod
    def _plans(material: CheckedReviewMaterial) -> list[tuple[AuthoringDraftMemberRef | None, NumericPlan]]:
        payload = material.payload
        if isinstance(payload, EditReviewMaterial):
            # This exact text-edit model contains no declared numeric plan.
            # Human applicability remains verified by Quality, never machine approval.
            return []
        if isinstance(payload, ImportReviewMaterial):
            if material.candidate.entity == 'question':
                raise blocked('PUBLISH_PRIVATE_COVERAGE_UNAVAILABLE', '当前导入审核不包含私有解答，不能据此准入题目发布。')
            if not isinstance(payload.payload, BlockDraftPayload):
                raise blocked('PUBLISH_MEMBER_COVERAGE_UNAVAILABLE', '当前导入审核只有对象元数据，缺少发布所需的完整成员材料。')
            if payload.payload.metadata.kind == 'worked_example':
                raise blocked('PUBLISH_NUMERIC_COVERAGE_UNAVAILABLE', '当前导入例题没有可核验的数值执行历史。')
            return []
        if isinstance(payload, SingleReviewMaterial):
            return [(None, payload.record.payload.numeric_plan)]
        assert isinstance(payload, GroupReviewMaterial)
        if payload.record.payload.questions:
            # §12.4 requires these actual checks. The current owner explicitly
            # reports NOT_RUN; whole-root human math/source fields cannot fill
            # those absent facts. A later real evidence port may support them.
            raise blocked('PUBLISH_QUESTION_QUALITY_UNCHECKED',
                '题目唯一性、干扰项、条件、单位、解答评分语义、目标及先修质量尚无完整检查证据。')
        return [(member_ref(block), block.payload.numeric_plan) for block in payload.record.payload.blocks
                if isinstance(block.payload, WorkedExamplePayload)]

    @staticmethod
    def _matching(check: NumericReviewCheck, target: AuthoringDraftMemberRef | None, plan: NumericPlan) -> bool:
        view = check.view
        if target is None:
            target_matches = not isinstance(view, AuthoringGroupNumericCheckView)
        else:
            target_matches = (isinstance(view, AuthoringGroupNumericCheckView)
                and canonical_bytes(view.target) == canonical_bytes(target))
        return target_matches and canonical_bytes(view.plan) == canonical_bytes(plan)

    @staticmethod
    def _passed(check: NumericReviewCheck) -> bool:
        view, job, start, end = check.view, check.job, check.start, check.end
        return bool(view.decision == 'approve_once' and check.record.decision_actor_id is not None
            and job is not None and job.status == 'completed' and check.input is not None
            and start is not None and start.admitted_at is not None and start.actual_started_at is not None
            and end is not None and end.output_complete and end.stdout_base64
            and end.result.outcome == 'passed' and end.result.verdict == 'PASS' and end.result.exit_code == 0
            and end.result.started_at == start.actual_started_at and end.result.output_sha256 is not None
            and end.result.assertions and all(x.passed and x.error_code is None for x in end.result.assertions))

    def check(self, connection: sqlite3.Connection, identity: SessionIdentity,
              draft_id: str, body: DraftPublishWrite) -> PublicationAdmission:
        body = validated(DraftPublishWrite, body)
        history, material = self.reviews.read_publication_basis(connection, identity, body.review_receipt_id)
        if (not history.records or not isinstance(history.records[0], ReviewMachineRecord)
                or not isinstance(history.records[-1], ReviewDecisionRecord)):
            raise blocked('PUBLISH_HUMAN_REVIEW_REQUIRED', '发布准入需要绑定此候选的明确人工审核决定。')
        return self._evaluate(material, history.records[0], history.records[-1], draft_id, body)

    def verify_recorded(self, connection: sqlite3.Connection, identity: SessionIdentity,
                        draft_id: str, body: DraftPublishWrite, expected: PublicationAdmission) -> None:
        """Verify a committed historical observation, never authorize a new publish.

        Read the complete current chain and all bytes first; later decisions stay
        authenticated even though this comparison names one original revision.
        The caller separately proves an actual immutable publication/command.
        """
        body, expected = validated(DraftPublishWrite, body), validated(PublicationAdmission, expected)
        history, material = self.reviews.read_publication_basis(connection, identity, body.review_receipt_id)
        matches = [r for r in history.records if isinstance(r, ReviewDecisionRecord)
                   and r.receipt.revision == expected.review_revision
                   and metadata_sha256(r.receipt) == expected.receipt_sha256]
        if not history.records or not isinstance(history.records[0], ReviewMachineRecord) or len(matches) != 1:
            raise blocked('PUBLISH_RECORDED_ADMISSION_INVALID', '原发布的审核观察无法完整核验。')
        actual = self._evaluate(material, history.records[0], matches[0], draft_id, body)
        if canonical_bytes(actual) != canonical_bytes(expected):
            raise blocked('PUBLISH_RECORDED_ADMISSION_INVALID', '原发布的准入观察与真实所属事实不符。')

    def _evaluate(self, material: CheckedReviewMaterial, machine: ReviewMachineRecord,
                  human: ReviewDecisionRecord, draft_id: str, body: DraftPublishWrite) -> PublicationAdmission:
        candidate = material.candidate
        if (candidate.draft_id != draft_id or candidate.draft_revision != body.expected_revision
                or candidate.candidate_sha256 != body.expected_content_sha256):
            raise ApiError(412, 'PUBLISH_CANDIDATE_MISMATCH', '发布请求与审核的精确候选版本不一致。')
        if machine.structural_report.structural != 'PASS':
            raise blocked('PUBLISH_STRUCTURE_REQUIRED', '结构检查尚未通过，不能准入发布。')
        if human.receipt.mathematical not in {'APPROVED', 'NOT_APPLICABLE'} or human.receipt.sources not in {'APPROVED', 'NOT_APPLICABLE'}:
            raise blocked('PUBLISH_HUMAN_REVIEW_REQUIRED', '数学与来源的适用审核尚未批准。')
        # Mathematical applicability was already checked against actual material
        # by the Quality owner while authenticating this exact human history.
        if human.receipt.sources == 'NOT_APPLICABLE' and (
                isinstance(material.payload, ImportReviewMaterial) or material.source_refs):
            raise blocked('PUBLISH_SOURCE_REVIEW_REQUIRED', '材料存在真实来源，不能以来源不适用替代审核。')
        plans = self._plans(material)
        selected: list[str] = []
        for target, plan in plans:
            matches = [check for check in machine.numeric.checks if self._matching(check, target, plan)]
            # Original owner order is persisted SQLite insertion order, verified
            # by ReviewNumeric's exact prefix checks, not wall-clock ordering.
            # A new check cannot make us reuse an earlier preferred PASS.
            if not matches or not self._passed(matches[-1]):
                raise blocked('PUBLISH_NUMERIC_REQUIRED', '审核所记录的数值历史缺少全部所需成员的完整通过结果。')
            selected.append(matches[-1].view.id)
        warnings = [*material.warnings, *(warning for check in machine.numeric.checks for warning in check.view.warnings)]
        if any(warning.severity == 'error' for warning in warnings):
            raise blocked('PUBLISH_OWNER_ERROR_UNRESOLVED', '实际所属材料仍包含未解决的错误。')
        acknowledged = set(body.acknowledged_warning_codes)
        known = {warning.code for warning in warnings}
        if acknowledged - known:
            raise ApiError(422, 'PUBLISH_WARNING_CODES_INVALID', '警告确认包含当前所属材料中不存在的代码。')
        if {warning.code for warning in warnings if warning.severity == 'warning'} - acknowledged:
            raise blocked('PUBLISH_WARNINGS_UNACKNOWLEDGED', '需要明确确认当前材料的全部实际警告。')
        return PublicationAdmission(version='publication-admission-observation-v1', workspace_id=material.workspace_id,
            candidate=candidate, review_receipt_id=human.review_id, review_revision=human.receipt.revision,
            receipt_sha256=metadata_sha256(human.receipt), material_descriptor_sha256=material.descriptor_sha256,
            numeric_observation_sha256=machine.numeric.descriptor_sha256, numeric_check_ids=selected,
            numeric_coverage='complete' if plans else 'not_required_by_material',
            acknowledged_warning_codes=list(body.acknowledged_warning_codes), publication='NOT_RUN')
