"""Internal candidate identity only; this is neither a review nor publication permission."""

from dataclasses import dataclass
from typing import Literal

from packages.contracts import domain_models as dm

DraftOwner = Literal['import', 'authoring']
DraftSourceKind = Literal['import', 'authoring_single', 'authoring_group']


@dataclass(frozen=True)
class ResolvedDraftCandidate:
    workspace_id: str
    owner: DraftOwner
    source_kind: DraftSourceKind
    candidate: dm.DraftCandidate


def match_candidate(expected: dm.DraftCandidate, actual: dm.DraftCandidate) -> None:
    from .errors import ApiError

    if expected.draft_id != actual.draft_id:
        raise ApiError(404, 'DRAFT_CANDIDATE_MISSING', '草稿候选不存在或不可访问。')
    if expected.draft_revision != actual.draft_revision:
        raise ApiError(412, 'DRAFT_REVISION_MISMATCH', '草稿版本已变化，请重新读取。')
    if expected != actual:
        raise ApiError(409, 'DRAFT_CANDIDATE_MISMATCH', '草稿类型或内容哈希不匹配。')
