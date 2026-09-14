from pathlib import Path

import pytest

from scripts.extract_spec import extract

ROOT = Path(__file__).resolve().parents[2]


def source(tmp_path: Path, entries: list[tuple[str, str]]) -> Path:
    spec = tmp_path / "input.md"
    spec.write_text("\n".join(f"<!-- BEGIN FILE: {name} -->\n~~~python\n{body}\n~~~\n<!-- END FILE -->" for name, body in entries))
    return spec


def test_single_document_extraction_is_idempotent(tmp_path):
    result = extract(ROOT / "PRODUCT_DESIGN.md", tmp_path)
    assert len(result) == 6
    assert extract(ROOT / "PRODUCT_DESIGN.md", tmp_path) == result
    assert (tmp_path / "packages/contracts/domain_models.py").exists()


def test_extraction_refuses_overwrite_before_writing_any_file(tmp_path):
    destination = tmp_path / "destination"
    destination.mkdir()
    edited = destination / "existing.py"
    edited.write_text("user work\n")
    spec = source(tmp_path, [("new.py", "new"), ("existing.py", "spec")])
    with pytest.raises(ValueError, match="edited destination"):
        extract(spec, destination)
    assert edited.read_text() == "user work\n"
    assert not (destination / "new.py").exists()


@pytest.mark.parametrize("path", ["../escape.py", "/escape.py", "a/../escape.py", "a//escape.py", "./escape.py"])
def test_extraction_rejects_path_escape(tmp_path, path):
    with pytest.raises(ValueError):
        extract(source(tmp_path, [(path, "x")]), tmp_path / "destination")


def test_extraction_rejects_escaping_symlink(tmp_path):
    destination = tmp_path / "destination"
    destination.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (destination / "nested").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escape"):
        extract(source(tmp_path, [("nested/escape.py", "x")]), destination)
    assert not (outside / "escape.py").exists()


def test_extraction_rejects_duplicate_paths(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        extract(source(tmp_path, [("a.py", "x"), ("a.py", "x")]), tmp_path / "destination")
