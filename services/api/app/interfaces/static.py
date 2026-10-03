"""Keep the root UI mount from taking over reserved API method matching."""
from starlette.routing import Match, Mount
from starlette.types import Scope


class WorkbenchStaticMount(Mount):
    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        path = scope.get("path", "")
        if scope["type"] == "http" and (path == "/api" or path.startswith("/api/") or path == "/health"):
            return Match.NONE, {}
        return super().matches(scope)
