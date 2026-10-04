"""Jobs-owned lifecycle adapter for Codex; no Authoring record is accepted."""
from .authoring_job_repository import AuthoringJobRepository


class CodexTurnJobs(AuthoringJobRepository):
    kinds = frozenset({'codex_turn'})

    @staticmethod
    def initial_status(kind: str) -> str:
        return 'awaiting_approval'
