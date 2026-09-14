"""Narrow synthetic SQLite regression for frozen concept dependencies.

Run from the repository root with:
    .venv/bin/python -B progress/evidence/2026-09-14/M2.1-independent-review-probe.py

Only a fresh temporary workspace is written. No real learning data or providers
are used; success is not a milestone-wide acceptance result.
"""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

# Standalone evidence runner bootstraps the repository path before local imports.
from packages.contracts import domain_models as dm  # noqa: E402
from packages.contracts.canonical import metadata_sha256, sha256_bytes  # noqa: E402
from services.api.app.application.content import ContentService  # noqa: E402
from services.api.app.config import Settings  # noqa: E402
from services.api.app.database import Database  # noqa: E402

SOURCE_PATHS = (
    "PRODUCT_DESIGN.md",
    "services/api/app/application/content.py",
    "services/api/app/content_dto.py",
    "services/api/app/infrastructure/content_repository.py",
    "services/api/app/infrastructure/blobs.py",
    "services/api/app/infrastructure/database.py",
    "services/api/app/infrastructure/config.py",
    "services/api/app/infrastructure/security.py",
    "packages/contracts/canonical.py",
    "packages/contracts/domain_models.py",
    "packages/contracts/validation.py",
    "migrations/0001_baseline.sql",
    "progress/evidence/2026-09-14/M2.1-independent-review-probe.py",
)


def hashes():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS}


def reference(value):
    return dm.ContentRef(
        entity=value.entity, id=value.id, revision=value.revision,
        sha256=metadata_sha256(value),
    )


def concept_dependencies(database, owner_id, revision):
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT target_id,target_revision FROM object_dependencies "
            "WHERE owner_id=? AND owner_revision=? AND relation='concept' ORDER BY target_id,target_revision",
            (owner_id, revision),
        ).fetchall()
    return [[row["target_id"], row["target_revision"]] for row in rows]


def main():
    before = hashes()
    with TemporaryDirectory(prefix="m2-independent-synthetic-") as directory:
        database = Database(Settings(data_dir=Path(directory) / "data"))
        database.initialize()
        workspace = database.workspace_id()
        service = ContentService(database)
        a1 = dm.Concept(
            id="concept_a_probe", revision=1, title="Synthetic A v1",
            prerequisite_ids=["concept_b_probe"],
        )
        b1 = dm.Concept(id="concept_b_probe", revision=1, title="Synthetic B v1")
        body = b"synthetic\n"
        block = dm.ContentBlock(
            id="block_probe", revision=1, kind="text", title="Synthetic",
            body_path="content/probe.md", body_sha256=sha256_bytes(body),
        )
        lesson = dm.Lesson(
            id="lesson_probe", revision=1, title="Synthetic", objectives=[],
            block_refs=[reference(block)],
        )
        course1 = dm.Course(
            id="course_probe", revision=1, title="Synthetic", audience="Probe",
            lesson_refs=[reference(lesson)], concept_refs=[reference(a1)],
        )
        service.publish(workspace, [b1, a1, block, lesson, course1], {block.body_path: body})
        initial_dependency = concept_dependencies(database, a1.id, 1)
        assert initial_dependency == [[b1.id, 1]]

        a2 = dm.Concept(id=a1.id, revision=2, title="Synthetic A v2")
        b2 = dm.Concept(id=b1.id, revision=2, title="Synthetic B v2", prerequisite_ids=[a1.id])
        service.publish(workspace, [a2, b2], {})
        assert service.current(workspace, a1.id) == reference(a2)
        assert service.current(workspace, b1.id) == reference(b2)
        assert service.read(workspace, "course", course1.id, 1) == course1

        course2 = course1.model_copy(update={"revision": 2})
        published = service.publish(workspace, [course2], {})
        assert published == [reference(course2)]
        assert service.current(workspace, course1.id) == reference(course2)
        assert service.read(workspace, "course", course1.id, 1) == course1
        assert service.read(workspace, "course", course1.id, 2) == course2
        assert service.body(workspace, block.id, 1) == (body, block.body_sha256)

        course1_dependencies = concept_dependencies(database, course1.id, 1)
        course2_dependencies = concept_dependencies(database, course1.id, 2)
        expected = [[a1.id, 1], [b1.id, 1]]
        assert course1_dependencies == expected
        assert course2_dependencies == expected
        assert concept_dependencies(database, a1.id, 1) == initial_dependency
        with database.connect() as connection:
            foreign_key_errors = [list(row) for row in connection.execute("PRAGMA foreign_key_check")]
            course_edges = [list(row) for row in connection.execute(
                "SELECT course_revision,prerequisite_id,dependent_id FROM concept_edges "
                "WHERE course_id=? ORDER BY course_revision,prerequisite_id,dependent_id", (course1.id,),
            )]
        assert foreign_key_errors == []
        assert course_edges == [[1, b1.id, a1.id], [2, b1.id, a1.id]]

    after = hashes()
    assert after == before, "Reviewed source changed during the narrow probe"
    result = {
        "status": "PASS",
        "scope": "Only the frozen concept dependency regression; not M2.1 or M2 acceptance",
        "data": "Synthetic objects in a fresh temporary native SQLite workspace, deleted after the run",
        "executed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
        "original_a1_dependency": initial_dependency,
        "concept_current_revisions": {a1.id: 2, b1.id: 2},
        "republish_old_exact_refs": "accepted",
        "course1_concept_dependencies": course1_dependencies,
        "course2_concept_dependencies": course2_dependencies,
        "course_concept_edges": course_edges,
        "old_course_and_body_readable": True,
        "foreign_key_check": foreign_key_errors,
        "source_hash_algorithm": "SHA-256 of each listed relative path's exact file bytes",
        "source_sha256": before,
        "source_unchanged_during_run": after == before,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
