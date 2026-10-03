"""Safe application failures independent of an HTTP framework."""

from dataclasses import dataclass


@dataclass
class ApiError(Exception):
    status: int
    code: str
    message: str
    retryable: bool = False
