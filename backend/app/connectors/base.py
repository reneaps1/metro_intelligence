"""F4.5 (MI-25): the connector contract. One connector = one way of turning
raw file bytes into rows of string-keyed data. Structural/safety validation
(type, magic bytes, zip-bomb guards) is part of the contract too, since it's
format-specific -- the import service never inspects file bytes directly,
only calls ``validate`` then ``parse_rows`` on whichever connector claims the
file's extension (CLAUDE.md §3: no engine/service depends on a specific
source; watched-folder and PolyWorks connectors will implement this same
interface later without either app code or the DB schema changing)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


class FileValidationError(Exception):
    """Raised when a file fails format/safety validation before parsing.
    The message is safe to return to the caller as-is -- no internals."""


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    data: dict[str, str]


class ImportConnector(ABC):
    @abstractmethod
    def validate(self, content: bytes, filename: str) -> None:
        """Raise FileValidationError if ``content`` isn't a safe, well-formed
        file of this connector's expected type. Structural checks only --
        never parses/evaluates the data itself."""

    @abstractmethod
    def parse_rows(self, content: bytes) -> Iterator[ParsedRow]:
        """Yield one ParsedRow per data row. Only ever called after a
        successful ``validate()`` on the same content."""
