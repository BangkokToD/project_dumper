from __future__ import annotations

from enum import Enum, auto
from typing import Iterable, List, Optional, Sequence, Set, Tuple
import re


class DiffLineType(Enum):
    """Тип строки диффа для подсветки."""

    PLUS = auto()
    MINUS = auto()
    HEADER_DIFF = auto()
    HEADER_HUNK = auto()
    HEADER_HUNK_EMPTY = auto()
    OTHER = auto()


_RE_HUNK_HEADER = re.compile(r"^(\s*@@.*?@@)")
_RE_DIFF_HEADER = re.compile(r"^\s*diff\b")


def detect_diff_block_indices(lines: Sequence[str]) -> Set[int]:
    """
    Найти индексы строк, относящихся к блокам заголовков diff.

    Правила (обновлённые):
    - Строка считается заголовком diff, если (после ведущих пробелов)
      начинается с 'diff' (например, 'diff --git a/... b/...').
    - Эта строка ВСЕГДА серая.
    - Далее БЕЗУСЛОВНО берём максимум следующие три строки (если они существуют)
      и тоже считаем их частью серого блока — независимо от содержимого.
    """
    result: Set[int] = set()
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        if _RE_DIFF_HEADER.match(line):
            # сама строка с diff всегда в блоке
            result.add(i)
            # следующие до трёх строк — всегда, независимо от содержимого
            for k in range(1, 4):
                j = i + k
                if j >= n:
                    break
                result.add(j)
        i += 1
    return result


def find_hunk_header_prefix(line: str) -> Optional[slice]:
    """
    Найти префикс '@@ ... @@' в начале строки (с учётом ведущих пробелов/табов).

    Возвращает slice, покрывающий:
      - все ведущие пробелы/табы перед @@,
      - сам сегмент @@ ... @@,
    либо None, если такой префикс не найден.

    ВАЖНО: функция сама по себе не знает про '+'/'-' в начале строки.
    Ограничение "не применять к строкам, начинающимся с +/-" должно
    обеспечиваться вызывающим кодом.
    """
    m = _RE_HUNK_HEADER.match(line)
    if not m:
        return None
    return slice(m.start(1), m.end(1))

def _is_empty_hunk_header(line: str) -> bool:
    """
    Пустой хедер '@@ ... @@' без текста между парами собачек.

    Примеры пустых:
      "@@"
      "@@    @@"
      "   @@   @@   "

    Непустые:
      "@@ -1,3 +1,4 @@"
    """
    stripped = line.lstrip()
    if not stripped.startswith("@@"):
        return False

    rest = stripped[2:]
    second_pos = rest.find("@@")
    if second_pos == -1:
        # только одна пара "@@" и больше ничего — тоже считаем пустым
        return True

    inner = rest[:second_pos]
    return inner.strip() == ""

def strip_for_copy(line: str) -> str:
    """
    Подготовка строки к копированию в буфер по правилам ТЗ.

    Алгоритм:
    1) Если строка НЕ начинается с '+' или '-' (первый символ),
       пробуем удалить префикс вида '  @@ ... @@' в начале строки,
       включая ведущие пробелы/табы.
    2) После этого удаляем ПЕРВЫЙ символ оставшейся строки (если он есть).

    Примеры:
      '+++abc'           -> '++abc'
      '+@@ -1,3 @@ foo'  -> '@@ -1,3 @@ foo'  (@@ не служебный, т.к. после '+')
      '@@ -1,3 @@ foo'   -> 'foo'
      '  @@ -1,3 @@ bar' -> 'bar'
      ''                 -> ''
    """
    # Пустые хедеры @@...@@ не копируем вообще
    if _is_empty_hunk_header(line):
        return ""

    s = line

    # Шаг 1: служебный хедер@@ в начале строки, только если первый символ
    # НЕ '+' и НЕ '-'. В противном случае @@ считаем обычным текстом.
    if s and s[0] not in {"+", "-"}:
        sl = find_hunk_header_prefix(s)
        if sl is not None and sl.start == 0:
            s = s[sl.stop :]

    # Шаг 2: удалить первый символ оставшейся строки
    if s:
        s = s[1:]
    return s


def get_group_indices(lines: Sequence[str], index: int) -> List[int]:
    """
    Найти группу строк для копирования при зажатом модификаторе (Ctrl/Shift и т. п.).

    Правила:
    - Если строка на позиции index начинается с '+' или '-':
        берём максимально широкий блок подряд идущих строк с тем же знаком
        (как и раньше).
    - Если строка начинается с пробела или таба:
        берём максимально широкий блок подряд идущих строк, у которых
        первый символ тоже пробел или таб (искусственный контекстный блок).
    - Во всех остальных случаях: возвращаем только [index].
    """
    if index < 0 or index >= len(lines):
        return []

    line = lines[index]
    if not line:
        return [index]

    first = line[0]

    # Группы изменений: '+', '-'
    if first in {"+", "-"}:
        sign = first
        start = index
        while start - 1 >= 0 and lines[start - 1].startswith(sign):
            start -= 1

        end = index
        n = len(lines)
        while end + 1 < n and lines[end + 1].startswith(sign):
            end += 1

        return list(range(start, end + 1))

    # Группы контекста: строки, начинающиеся с пробела или таба.
    if first in {" ", "\t"}:
        start = index
        while (
            start - 1 >= 0
            and lines[start - 1]
            and lines[start - 1][0] in {" ", "\t"}
        ):
            start -= 1

        end = index
        n = len(lines)
        while (
            end + 1 < n
            and lines[end + 1]
            and lines[end + 1][0] in {" ", "\t"}
        ):
            end += 1

        return list(range(start, end + 1))

    # Всё остальное — одиночная строка.
    return [index]



def classify_line(
    lines: Sequence[str],
    index: int,
    diff_block_indices: Set[int],
) -> DiffLineType:
    """
    Определить тип строки для подсветки.

    Приоритет:
      1) Если индекс входит в diff_block_indices -> HEADER_DIFF.
      2) Если (после ведущих пробелов) строка начинается с '@@' -> HEADER_HUNK.
      3) Если первый символ '+' -> PLUS.
      4) Если первый символ '-' -> MINUS.
      5) Иначе -> OTHER.
    """
    if index < 0 or index >= len(lines):
        return DiffLineType.OTHER

    if index in diff_block_indices:
        return DiffLineType.HEADER_DIFF

    line = lines[index]
    # сначала проверяем "пустой" хедер @@...@@ без содержания
    if _is_empty_hunk_header(line):
        return DiffLineType.HEADER_HUNK_EMPTY
    if _RE_HUNK_HEADER.match(line):
        return DiffLineType.HEADER_HUNK

    if line.startswith("+"):
        return DiffLineType.PLUS
    if line.startswith("-"):
        return DiffLineType.MINUS
    return DiffLineType.OTHER
