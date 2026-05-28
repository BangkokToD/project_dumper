from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping

from domain.term_replace.models import (
    ReplacementPreview,
    ReplacementPreviewChange,
    ReplacementPreviewFile,
    ReplacementRule,
)

_RUSSIAN_LETTER_PATTERN = "А-Яа-яЁё"


def build_replacement_preview(
    files: Mapping[str, str],
    rules: Iterable[ReplacementRule],
) -> ReplacementPreview:
    """Построить preview замен по содержимому файлов.

    Функция не работает с файловой системой и принимает уже прочитанные тексты.
    Каждое найденное вхождение формирует отдельный ``ReplacementPreviewChange``.

    Args:
        files: Отображение ``путь файла -> содержимое файла``.
        rules: Правила замены найденных форм.

    Returns:
        Preview изменений, сгруппированный по файлам.
    """
    active_rules = _active_rules_by_source(rules)
    if not active_rules:
        return ReplacementPreview(files=[])

    preview_files: list[ReplacementPreviewFile] = []

    for file_path, content in files.items():
        changes = _build_changes_for_file(
            file_path=file_path,
            content=content,
            rules=active_rules,
        )
        if not changes:
            continue

        preview_files.append(
            ReplacementPreviewFile(
                file_path=file_path,
                content_hash=_content_hash(content),
                changes=changes,
            )
        )

    return ReplacementPreview(files=preview_files)


def _active_rules_by_source(
    rules: Iterable[ReplacementRule],
) -> dict[str, ReplacementRule]:
    """Отобрать включённые правила с непустой заменой.

    Args:
        rules: Правила замены.

    Returns:
        Словарь ``исходная форма -> правило``. При дублях используется
        последнее правило, чтобы результат был детерминированным.
    """
    active: dict[str, ReplacementRule] = {}

    for rule in rules:
        source = rule.source.strip()
        if not source:
            continue
        if not rule.enabled:
            continue
        if rule.replacement == "":
            continue
        active[source] = rule

    return active


def _build_changes_for_file(
    *,
    file_path: str,
    content: str,
    rules: Mapping[str, ReplacementRule],
) -> list[ReplacementPreviewChange]:
    """Построить список preview-изменений для одного файла.

    Args:
        file_path: Относительный POSIX-путь файла.
        content: Содержимое файла.
        rules: Активные правила замены по исходной форме.

    Returns:
        Список конкретных изменений в порядке обхода файла.
    """
    changes: list[ReplacementPreviewChange] = []
    patterns = {
        source: _build_exact_source_pattern(source)
        for source in rules
    }

    for line_number, line_text in enumerate(content.splitlines(), start=1):
        line_matches: list[tuple[int, int, ReplacementRule]] = []

        for source, pattern in patterns.items():
            rule = rules[source]
            for match in pattern.finditer(line_text):
                line_matches.append((match.start(), match.end(), rule))

        line_matches.sort(key=lambda item: (item[0], item[1], item[2].source))

        for start, end, rule in line_matches:
            line_after = (
                line_text[:start]
                + rule.replacement
                + line_text[end:]
            )
            changes.append(
                ReplacementPreviewChange(
                    id=_change_id(file_path, line_number, start, end, rule.source),
                    file_path=file_path,
                    line_number=line_number,
                    column_start=start,
                    column_end=end,
                    source=rule.source,
                    replacement=rule.replacement,
                    line_before=line_text,
                    line_after=line_after,
                )
            )

    return changes


def _build_exact_source_pattern(source: str) -> re.Pattern[str]:
    """Собрать regex для точной найденной формы с русскими границами слова.

    Args:
        source: Точная найденная форма из правила замены.

    Returns:
        Скомпилированное регулярное выражение.
    """
    escaped_source = re.escape(source)
    return re.compile(
        rf"(?<![{_RUSSIAN_LETTER_PATTERN}])"
        rf"{escaped_source}"
        rf"(?![{_RUSSIAN_LETTER_PATTERN}])"
    )


def _content_hash(content: str) -> str:
    """Посчитать hash содержимого файла для проверки устаревания preview.

    Args:
        content: Исходное содержимое файла.

    Returns:
        SHA-256 hash в hex-формате.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _change_id(
    file_path: str,
    line_number: int,
    column_start: int,
    column_end: int,
    source: str,
) -> str:
    """Сформировать стабильный идентификатор изменения внутри preview.

    Args:
        file_path: Относительный POSIX-путь файла.
        line_number: Номер строки.
        column_start: Начальная колонка.
        column_end: Конечная колонка.
        source: Исходная форма.

    Returns:
        Строковый идентификатор изменения.
    """
    return f"{file_path}:{line_number}:{column_start}:{column_end}:{source}"