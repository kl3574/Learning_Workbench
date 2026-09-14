"""Parser values are candidates, never a publication or mathematical approval."""

from dataclasses import dataclass
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.validation import PublishedModel

PARSER_VERSION = "learning-import-1"


class ImportParsingError(ValueError):
    def __init__(self, code: str, message: str, *, warnings: tuple[dm.Warning, ...] = ()):
        self.code = code
        self.warnings = warnings
        super().__init__(message)


@dataclass(frozen=True)
class ParsedAsset:
    path: str
    media_type: str
    visibility: Literal["learner", "author_private"]
    data: bytes


@dataclass(frozen=True)
class ParsedImport:
    objects: tuple[PublishedModel, ...]
    bodies: dict[str, bytes]
    solutions: tuple[dm.SolutionPrivate, ...]
    warnings: tuple[dm.Warning, ...]
    parser_version: str
    symbols: tuple[dm.Symbol, ...] = ()
    citations: tuple[dm.Citation, ...] = ()
    assets: tuple[ParsedAsset, ...] = ()
    quality_receipt: bytes | None = None
    package_profile: Literal["learner", "author"] | None = None
    original_visibility: Literal["learner", "author_private"] | None = None


def warning(code: str, message: str, locator: str | None = None) -> dm.Warning:
    return dm.Warning(code=code, message=message, locator=locator, severity="warning")
