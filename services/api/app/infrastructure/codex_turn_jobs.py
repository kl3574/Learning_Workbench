"""Jobs-owned lifecycle adapter for Codex; no Authoring record is accepted."""
from .authoring_job_repository import AuthoringJobRepository


class CodexTurnJobs(AuthoringJobRepository):
    kinds = frozenset({'codex_turn'})
    transitions = {**AuthoringJobRepository.transitions, 'queued': {'running', 'cancelled', 'failed'}}

    @staticmethod
    def initial_status(kind: str) -> str:
        return 'awaiting_approval'

    def queued_ids(self, limit: int = 32) -> list[str]:
        return [row[0] for row in self.conn.execute(
            "SELECT id FROM jobs WHERE workspace_id=? AND kind='codex_turn' AND status='queued' ORDER BY created_at,id LIMIT ?",
            (self.workspace_id, limit))]
