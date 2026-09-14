"""Fixed sandbox entry: no app, database, credentials, networking, or host paths."""

from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path[:0] = ["/", "/deps", "/extractors"]


def main() -> None:
    from sandbox_bootstrap import lock_execution  # type: ignore[import-not-found]
    lock_execution()
    from document_extract.import_extract_types import ExtractionFailure  # type: ignore[import-not-found]
    result: dict[str, object]
    try:
        options = json.loads(Path("/request.json").read_bytes())
        data = Path("/input.bin").read_bytes()
        if options["kind"] == "pdf":
            from document_extract.import_extract_pdf import extract_pdf  # type: ignore[import-not-found]
            document = extract_pdf(data, budgets=options["budgets"])
        elif options["kind"] == "docx":
            from document_extract.import_extract_docx import extract_docx  # type: ignore[import-not-found]
            document = extract_docx(data, budgets=options["budgets"])
        else:
            raise ValueError("Unsupported kind")
        result = {"status": "ok", "document": asdict(document)}
    except ExtractionFailure as error:
        result = {"status": "error", "code": error.code, "warnings": [asdict(warning) for warning in error.warnings]}
    except MemoryError:
        result = {"status": "error", "code": "EXTRACTION_RESOURCE_LIMIT", "warnings": []}
    except BaseException:
        result = {"status": "error", "code": "EXTRACTION_FAILED", "warnings": []}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
