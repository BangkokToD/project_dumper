from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

SelectedPathKind = Literal["pattern", "file", "dir", "missing"]


def is_pattern_token(token: str) -> bool:
    """
    Определить, является ли токен "паттерном".

    Критерий (как в ТЗ парсера): содержит '*', '?' или '['.
    """
    return ("*" in token) or ("?" in token) or ("[" in token)


def has_bad_bracket_syntax(pattern: str) -> bool:
    """
    Простая детерминированная проверка синтаксиса [] в паттерне.

    Считаем "плохим":
    - незакрытый '['
    - ']' без соответствующего '[' (вне класса)
    - пустой класс '[]'
    - пустой класс с отрицанием '[!]' / '[^]'

    Это НЕ полноценный glob-парсер — только fail-fast валидация скобок.
    """
    in_class = False
    class_has_content = False
    first_in_class = False

    for ch in pattern:
        if not in_class:
            if ch == "[":
                in_class = True
                class_has_content = False
                first_in_class = True
            elif ch == "]":
                # закрывающая скобка без открытия
                return True
            continue

        # внутри [...]
        if ch == "]":
            # закрытие класса: он не должен быть пустым
            if not class_has_content:
                return True
            in_class = False
            first_in_class = False
            continue

        # первый символ в классе может быть отрицанием, но контентом не считается
        if first_in_class and ch in ("!", "^"):
            first_in_class = False
            continue

        class_has_content = True
        first_in_class = False

    # если класс не закрыт
    return in_class


@dataclass(slots=True)
class SelectedPath:
    """
    Результат первичного разбора токена из "Списка" относительно корня проекта.

    Важно: здесь нет чтения файлов — только stat/exists/is_dir/is_file.
    """

    raw: str
    resolved: Path
    kind: SelectedPathKind
    bad_pattern_syntax: bool = False
    missing_reason: str | None = None



def _kind_for_path(p: Path, *, follow_symlinks: bool) -> SelectedPathKind:
    """
    Определить kind для НЕ-паттерна.
    Symlink обрабатывается в соответствии с follow_symlinks.
    """
    try:
        if p.is_symlink() and not follow_symlinks:
            return "missing"

        if not p.exists():
            return "missing"

        if p.is_dir():
            return "dir"
        if p.is_file():
            return "file"

        # спец-типы (device/fifo/etc) трактуем как missing для предсказуемости
        return "missing"
    except Exception:
        # permission / broken components / etc.
        return "missing"


def resolve_selected_path(root: Path, raw: str, *, follow_symlinks: bool = True) -> SelectedPath:
    """
    Преобразовать raw-токен в SelectedPath.

    - resolved = root / raw (без Path.resolve)
    - kind = pattern/file/dir/missing
    - bad_pattern_syntax: только для pattern (валидация [])
    """
    resolved = root / raw

    if is_pattern_token(raw):
        bad = has_bad_bracket_syntax(raw)
        return SelectedPath(raw=raw, resolved=resolved, kind="pattern", bad_pattern_syntax=bad)

    kind = _kind_for_path(resolved, follow_symlinks=follow_symlinks)
    return SelectedPath(raw=raw, resolved=resolved, kind=kind, bad_pattern_syntax=False)


def resolve_selected_paths(
    root: Path,
    raws: Iterable[str],
    *,
    follow_symlinks: bool = True,
) -> list[SelectedPath]:
    """
    Векторная версия resolve_selected_path (без фильтров/дедупа/чтения).
    """
    return [resolve_selected_path(root, raw, follow_symlinks=follow_symlinks) for raw in raws]
