from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TermOccurrence:
    """Одно найденное вхождение термина.

    Attributes:
        file_path: Относительный POSIX-путь файла.
        line_number: Номер строки, начиная с 1.
        column_start: Начальная колонка вхождения, начиная с 0.
        column_end: Конечная колонка вхождения, не включая символ на этой позиции.
        matched_text: Точный найденный текст с сохранением исходного регистра.
        line_text: Полная строка, в которой найдено вхождение.
    """

    file_path: str
    line_number: int
    column_start: int
    column_end: int
    matched_text: str
    line_text: str


@dataclass(slots=True)
class TermVariant:
    """Группа одинаковых написаний найденного термина.

    Attributes:
        text: Точное найденное написание формы.
        count: Общее количество вхождений формы.
        file_count: Количество файлов, где встретилась форма.
        occurrences: Конкретные вхождения этой формы.
    """

    text: str
    count: int
    file_count: int
    occurrences: list[TermOccurrence]


@dataclass(slots=True)
class ReplacementRule:
    """Правило замены одной найденной формы.

    Attributes:
        source: Исходная найденная форма.
        replacement: Текст замены.
        enabled: Участвует ли правило в preview и применении.
    """

    source: str
    replacement: str
    enabled: bool = True


@dataclass(slots=True)
class ReplacementPreviewChange:
    """Одно конкретное изменение в preview.

    Attributes:
        id: Стабильный идентификатор изменения внутри одного preview.
        file_path: Относительный POSIX-путь файла.
        line_number: Номер строки, начиная с 1.
        column_start: Начальная колонка заменяемого текста, начиная с 0.
        column_end: Конечная колонка заменяемого текста, не включая символ на этой позиции.
        source: Исходный текст конкретного вхождения.
        replacement: Текст замены.
        line_before: Строка до применения конкретной замены.
        line_after: Строка после применения только этой конкретной замены.
        enabled: Должно ли конкретное изменение применяться.
    """

    id: str
    file_path: str
    line_number: int
    column_start: int
    column_end: int
    source: str
    replacement: str
    line_before: str
    line_after: str
    enabled: bool = True


@dataclass(slots=True)
class ReplacementPreviewFile:
    """Preview изменений одного файла.

    Attributes:
        file_path: Относительный POSIX-путь файла.
        content_hash: Hash исходного содержимого файла на момент preview.
        changes: Конкретные изменения внутри файла.
    """

    file_path: str
    content_hash: str
    changes: list[ReplacementPreviewChange]


@dataclass(slots=True)
class ReplacementPreview:
    """Preview массовой замены по файлам.

    Attributes:
        files: Preview-файлы с конкретными изменениями.
    """

    files: list[ReplacementPreviewFile]


@dataclass(slots=True)
class ReplacementApplyReport:
    """Отчёт о применении замен.

    Attributes:
        changed_files: Количество реально изменённых файлов.
        applied_changes: Количество применённых изменений.
        skipped_changes: Количество пропущенных изменений.
        conflicted_files: Файлы, которые изменились после preview и не были записаны.
    """

    changed_files: int
    applied_changes: int
    skipped_changes: int
    conflicted_files: list[str]