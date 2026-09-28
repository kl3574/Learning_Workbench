"""Deterministic checks of complete material declarations, without owner authority.

The application must obtain the material from its actual owner in the current
transaction. Revalidating a self-consistent descriptor here does not authenticate
that history, validate mathematical prose, execute a plan or approve a source.
"""
from typing import Literal, Self

from pydantic import model_validator, ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from ..authoring_dto import AuthoringBlockRef, AuthoringModel, WorkedExamplePayload
from ..authoring_group_dto import AuthoringTextBlockPayload, GeneratedSolutionAnswer
from .errors import ApiError
from .review_material_models import (
    CheckedReviewMaterial, ImportReviewMaterial, SingleReviewMaterial, GroupReviewMaterial,
)

CheckCode = Literal['material_schema', 'candidate_byte_binding', 'declared_source_membership',
                    'declared_symbol_consistency']
CheckStatus = Literal['PASS', 'FAIL', 'NOT_RUN']
DetailCode = Literal['not_requested', 'typed_material_revalidated', 'candidate_and_body_hashes_revalidated',
                     'all_declared_sources_in_prepared_set', 'declared_source_outside_prepared_set',
                     'symbol_and_numeric_declarations_consistent', 'symbol_or_numeric_declaration_conflict',
                     'no_authoring_declaration_schema']
ORDER: tuple[CheckCode, ...] = ('material_schema', 'candidate_byte_binding',
                               'declared_source_membership', 'declared_symbol_consistency')
DETAILS: dict[tuple[CheckCode, CheckStatus], DetailCode] = {
    ('material_schema', 'PASS'): 'typed_material_revalidated',
    ('candidate_byte_binding', 'PASS'): 'candidate_and_body_hashes_revalidated',
    ('declared_source_membership', 'PASS'): 'all_declared_sources_in_prepared_set',
    ('declared_source_membership', 'FAIL'): 'declared_source_outside_prepared_set',
    ('declared_symbol_consistency', 'PASS'): 'symbol_and_numeric_declarations_consistent',
    ('declared_symbol_consistency', 'FAIL'): 'symbol_or_numeric_declaration_conflict',
}


class StructuralReviewCheck(AuthoringModel):
    code: CheckCode
    status: CheckStatus
    detail_code: DetailCode


class StructuralReviewReport(AuthoringModel):
    version: Literal['review-structure-report-v1']
    candidate: dm.DraftCandidate
    material_descriptor_sha256: dm.Sha256
    requested: bool
    structural: CheckStatus
    checks: list[StructuralReviewCheck]

    @model_validator(mode='after')
    def complete_scope(self) -> Self:
        if tuple(check.code for check in self.checks) != ORDER:
            raise ValueError('The report must retain the complete ordered check scope')
        if not self.requested:
            if self.structural != 'NOT_RUN' or any(
                    check.status != 'NOT_RUN' or check.detail_code != 'not_requested' for check in self.checks):
                raise ValueError('Unrequested structure checks cannot claim execution')
            return self
        for check in self.checks:
            expected = DETAILS.get((check.code, check.status))
            if check.status == 'NOT_RUN' and check.code in ORDER[2:]:
                expected = 'no_authoring_declaration_schema'
            if expected is None or check.detail_code != expected:
                raise ValueError('The detail must describe the actual named check boundary')
        expected_status = 'FAIL' if any(x.status == 'FAIL' for x in self.checks) else 'PASS'
        if self.structural != expected_status:
            raise ValueError('The aggregate cannot hide a failed check')
        return self


def _check(code: CheckCode, status: CheckStatus, detail: DetailCode | None = None) -> StructuralReviewCheck:
    return StructuralReviewCheck(code=code, status=status, detail_code=detail or DETAILS[(code, status)])


Declaration = WorkedExamplePayload | AuthoringTextBlockPayload | GeneratedSolutionAnswer


def _declarations(material: CheckedReviewMaterial) -> tuple[list[list[AuthoringBlockRef]], list[Declaration]]:
    """Return only explicit source/symbol declarations, never scrape prose."""
    payload = material.payload
    if isinstance(payload, SingleReviewMaterial):
        single = payload.record.payload
        return [single.declared_source_refs], [single]
    if isinstance(payload, GroupReviewMaterial):
        value = payload.record.payload
        if value.root.entity == 'lesson':
            return [block.payload.declared_source_refs for block in value.blocks], [block.payload for block in value.blocks]
        return [question.declared_source_refs for question in value.questions], [item.answer for item in value.private_solutions]
    return [], []


def review_structure(material: CheckedReviewMaterial, *, requested: bool) -> StructuralReviewReport:
    """Run named local checks; no database, file, Provider or NumericRuntime calls.

    Malformed purported owner material is an integrity error, not a fabricated
    receipt about an unbound candidate. Structurally valid foreign declarations
    can yield FAIL. Successful declarations never authenticate their meaning.
    """
    try:
        material = CheckedReviewMaterial.model_validate(material.model_dump(mode='python'))
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise ApiError(503, 'REVIEW_MATERIAL_INTEGRITY', '审核材料未通过完整性校验。') from None
    if not isinstance(requested, bool):
        raise ApiError(422, 'SCHEMA_INVALID', '结构检查选择无效。')
    if not requested:
        checks = [_check(code, 'NOT_RUN', 'not_requested') for code in ORDER]
        status: CheckStatus = 'NOT_RUN'
    else:
        # The complete model validation recomputes descriptor, candidate/body,
        # plan, member and private-solution relationships for its exact profile.
        checks = [_check('material_schema', 'PASS'), _check('candidate_byte_binding', 'PASS')]
        if isinstance(material.payload, ImportReviewMaterial):
            checks += [_check(code, 'NOT_RUN', 'no_authoring_declaration_schema') for code in ORDER[2:]]
        else:
            source_lists, declarations = _declarations(material)
            allowed = {canonical_bytes(ref) for ref in material.source_refs}
            references_ok = all(canonical_bytes(ref) in allowed for refs in source_lists for ref in refs)
            symbols_ok = True
            for declaration in declarations:
                names = [symbol.name for symbol in declaration.symbols]
                symbols_ok = symbols_ok and len(names) == len(set(names))
                plan = None if isinstance(declaration, AuthoringTextBlockPayload) else declaration.numeric_plan
                if plan is not None:
                    symbols_ok = symbols_ok and all(variable.name in names for variable in plan.variables)
            checks += [_check('declared_source_membership', 'PASS' if references_ok else 'FAIL'),
                       _check('declared_symbol_consistency', 'PASS' if symbols_ok else 'FAIL')]
        status = 'FAIL' if any(check.status == 'FAIL' for check in checks) else 'PASS'
    return StructuralReviewReport(version='review-structure-report-v1', candidate=material.candidate,
        material_descriptor_sha256=material.descriptor_sha256, requested=requested, structural=status, checks=checks)
