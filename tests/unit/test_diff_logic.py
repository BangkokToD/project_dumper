from __future__ import annotations

from project_dumper.diff_logic import (
    DiffLineType,
    classify_line,
    detect_diff_block_indices,
    find_hunk_header_prefix,
    get_group_indices,
    strip_for_copy,
)


def test_detect_diff_block_indices_basic() -> None:
    lines = [
        "diff --git a/x b/x",  # 0
        "",                    # 1
        "   ",                 # 2
        "",                    # 3
        "+line",               # 4
        "diff something",      # 5
        "not-empty",           # 6
        "",                    # 7
    ]

    indices = detect_diff_block_indices(lines)
    # Первый блок: заголовок + следующие три строки (без условий)
    assert {0, 1, 2, 3} <= indices
    # Второй блок: заголовок + три строки после него, независимо от содержимого
    # здесь реально доступны индексы 5,6,7
    assert {5, 6, 7} <= indices


def test_find_hunk_header_prefix_variants() -> None:
    line = "@@ -1,3 +1,4 @@ rest"
    sl = find_hunk_header_prefix(line)
    assert sl is not None
    assert line[sl] == "@@ -1,3 +1,4 @@"

    line2 = "  @@ -1,3 +1,4 @@ rest"
    sl2 = find_hunk_header_prefix(line2)
    assert sl2 is not None
    # Должны входить ведущие пробелы
    assert line2[sl2].startswith("  @@")
    assert line2[sl2].strip().startswith("@@")

    line3 = "no header here"
    assert find_hunk_header_prefix(line3) is None


def test_strip_for_copy_no_header() -> None:
    assert strip_for_copy("+abc") == "abc"
    assert strip_for_copy("-xyz") == "xyz"
    assert strip_for_copy("") == ""


def test_strip_for_copy_hunk_header_plain() -> None:
    line = "@@ -1,3 +1,4 @@ foo"
    # Удаляем префикс @@...@@ и первый символ остатка (пробел)
    assert strip_for_copy(line) == "foo"


def test_strip_for_copy_hunk_header_with_spaces() -> None:
    line = "   @@ -1,3 +1,4 @@ bar"
    # Удаляем "   @@ -1,3 +1,4 @@" и первый символ остатка (пробел)
    assert strip_for_copy(line) == "bar"


def test_strip_for_copy_header_not_at_start_due_to_plus() -> None:
    # Здесь первый символ '+', поэтому @@ не считается служебным заголовком
    line = "+@@ -1,3 +1,4 @@ foo"
    assert strip_for_copy(line) == "@@ -1,3 +1,4 @@ foo"


def test_strip_for_copy_empty_hunk_headers() -> None:
    # Пустые @@ полностью удаляются
    assert strip_for_copy("@@") == ""
    assert strip_for_copy("@@    @@") == ""
    assert strip_for_copy("   @@   @@   ") == ""

def test_get_group_indices_basic() -> None:
    lines = [
        "-a",   # 0
        "-b",   # 1
        " c",   # 2 (контекст, но одиночный)
        "+d",   # 3
        "+e",   # 4
        "-f",   # 5
    ]

    # Группа двух '-' подряд
    assert get_group_indices(lines, 1) == [0, 1]
    # Группа двух '+' подряд
    assert get_group_indices(lines, 3) == [3, 4]
    # Нейтральная строка — только сама по себе
    assert get_group_indices(lines, 2) == [2]
    # Одиночный '-'
    assert get_group_indices(lines, 5) == [5]

def test_get_group_indices_context_block() -> None:
    lines = [
        " header",     # 0 (context, пробел)
        "  more",      # 1 (context, пробел)
        "\tindented",  # 2 (context, таб)
        "+change",     # 3
    ]

    # Клик по 0: должен захватить все подряд строки с первым символом пробел/таб,
    # т. е. 0,1,2
    assert get_group_indices(lines, 0) == [0, 1, 2]

    # Клик по 1: тот же блок
    assert get_group_indices(lines, 1) == [0, 1, 2]

    # Клик по '+change': обычная группа '+' только из одной строки
    assert get_group_indices(lines, 3) == [3]


def test_get_group_indices_mixed_plus_minus() -> None:
    lines = [
        "-1",  # 0
        "+2",  # 1
        "-3",  # 2
    ]
    # При клике по '+2' группа только из одной строки
    assert get_group_indices(lines, 1) == [1]


def test_classify_line_priority() -> None:
    lines = [
        "diff --git a/x b/x",      # 0 HEADER_DIFF
        "",                        # 1 HEADER_DIFF
        "@@ -1,3 +1,4 @@ header",  # 2 HEADER_DIFF (входит в блок diff)
        "+added",                  # 3 HEADER_DIFF (3-я строка после diff)
        "-removed",                # 4 MINUS
        " context",                # 5 OTHER
    ]
    diff_indices = detect_diff_block_indices(lines)

    assert classify_line(lines, 0, diff_indices) is DiffLineType.HEADER_DIFF
    assert classify_line(lines, 1, diff_indices) is DiffLineType.HEADER_DIFF
    # из-за жёсткого правила diff + три строки всё до индекса 3 — HEADER_DIFF
    assert classify_line(lines, 2, diff_indices) is DiffLineType.HEADER_DIFF
    assert classify_line(lines, 3, diff_indices) is DiffLineType.HEADER_DIFF
    assert classify_line(lines, 4, diff_indices) is DiffLineType.MINUS
    assert classify_line(lines, 5, diff_indices) is DiffLineType.OTHER

    # Отдельно проверим, что хедер хунка вне diff-блока классифицируется как HEADER_HUNK
    lines2 = [
        "@@ -1,3 +1,4 @@ header",  # 0 HEADER_HUNK
        "+added",                   # 1 PLUS
    ]
    diff_indices2 = set()
    assert classify_line(lines2, 0, diff_indices2) is DiffLineType.HEADER_HUNK
    assert classify_line(lines2, 1, diff_indices2) is DiffLineType.PLUS


def test_classify_empty_hunk_header() -> None:
    lines = [
        "@@",          # 0 пустой хедер
        "@@   @@",     # 1 пустой хедер
        "   @@  @@  ", # 2 пустой хедер
    ]
    diff_indices: set[int] = set()
    assert classify_line(lines, 0, diff_indices) is DiffLineType.HEADER_HUNK_EMPTY
    assert classify_line(lines, 1, diff_indices) is DiffLineType.HEADER_HUNK_EMPTY
    assert classify_line(lines, 2, diff_indices) is DiffLineType.HEADER_HUNK_EMPTY