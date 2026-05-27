from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ListScanIssueKind = Literal[
    "missing",
    "bad_pattern_syntax",
    "zero_matches",
    "hidden",
    "skipped",
    "read_error",
]
ZeroMatchesReason = Literal["no_matches", "filtered_out"]


@dataclass(slots=True)
class ListScanIssueItem:
    value: str
    count: int = 1
    # только для zero_matches
    reason: ZeroMatchesReason | None = None
    # опционально (например, missing_reason для .env policy)
    detail: str | None = None


@dataclass(slots=True)
class ListScanIssueGroup:
    kind: ListScanIssueKind
    items: list[ListScanIssueItem]


@dataclass(slots=True)
class ListScanDiagnostics:
    groups: list[ListScanIssueGroup]


class ListScanValidationError(RuntimeError):
    """
    Контролируемая ошибка fail-fast для вкладки "Список".
    UI позже сможет показать модалку на основе diagnostics.
    """

    def __init__(self, diagnostics: ListScanDiagnostics):
        super().__init__("ListScan validation failed")
        self.diagnostics = diagnostics
