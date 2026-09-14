"""Explicit ingestion safety budgets; changing them does not relax schema semantics."""

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class ImportBudgets:
    max_source_bytes: int = 50 * 1024 * 1024
    max_block_characters: int = 400_000
    max_package_bytes: int = 200 * 1024 * 1024
    max_package_files: int = 2_000
    max_compression_ratio: int = 100

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field.name} must be a positive integer")
