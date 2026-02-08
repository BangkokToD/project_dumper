from __future__ import annotations

from pathlib import Path

import pytest

from config.model import Config
from domain.list_scan import ListScanValidationError
from services.scan_by_paths_service import ScanByPathsService


def _mk_proj(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    return root


def _get_group(diag, kind: str):
    for g in diag.groups:
        if g.kind == kind:
            return g
    raise AssertionError(f"Group {kind!r} not found. Have: {[g.kind for g in diag.groups]}")


def _assert_single_item(group, *, value: str, reason: str | None = None, count: int = 1):
    assert len(group.items) == 1
    it = group.items[0]
    assert it.value == value
    assert it.count == count
    if reason is not None:
        assert it.reason == reason


def test_case_10_glob_py_matches_only_root_level_when_star_is_recursive_off(tmp_path: Path) -> None:
    """
    10. `*.py` → включает только root/*.py при выключенной настройке “* рекурсивная”.
    """
    root = _mk_proj(tmp_path)
    (root / "a.py").write_text("print('a')\n", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "b.py").write_text("print('b')\n", encoding="utf-8")

    cfg = Config()
    cfg.list_scan.star_is_recursive = False

    res = ScanByPathsService.scan(root, ["*.py"], cfg, cfg.list_scan)
    assert [f.path for f in res.files] == ["a.py"]


def test_case_11_domain_star_default_first_level_only(tmp_path: Path) -> None:
    """
    11. `domain/*` → только файлы первого уровня в domain (директории не разворачиваются).
    """
    root = _mk_proj(tmp_path)
    (root / "domain").mkdir()
    (root / "domain" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (root / "domain" / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "domain" / "sub").mkdir()
    (root / "domain" / "sub" / "b.py").write_text("print('b')\n", encoding="utf-8")

    cfg = Config()
    cfg.list_scan.star_is_recursive = False
    cfg.list_scan.expand_dir_match = False

    res = ScanByPathsService.scan(root, ["domain/*"], cfg, cfg.list_scan)
    assert [f.path for f in res.files] == ["domain/a.py", "domain/a.txt"]


def test_case_12_domain_double_star_recursive(tmp_path: Path) -> None:
    """
    12. `domain/**` → рекурсивно.
    """
    root = _mk_proj(tmp_path)
    (root / "domain").mkdir()
    (root / "domain" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (root / "domain" / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "domain" / "sub").mkdir()
    (root / "domain" / "sub" / "b.py").write_text("print('b')\n", encoding="utf-8")

    cfg = Config()
    res = ScanByPathsService.scan(root, ["domain/**"], cfg, cfg.list_scan)
    assert [f.path for f in res.files] == ["domain/a.py", "domain/a.txt", "domain/sub/b.py"]


def test_case_13_star_is_recursive_on_makes_domain_star_recursive(tmp_path: Path) -> None:
    """
    13. “* рекурсивная” включена: `domain/*` → рекурсивно.
    """
    root = _mk_proj(tmp_path)
    (root / "domain").mkdir()
    (root / "domain" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (root / "domain" / "sub").mkdir()
    (root / "domain" / "sub" / "b.py").write_text("print('b')\n", encoding="utf-8")

    cfg = Config()
    cfg.list_scan.star_is_recursive = True

    res = ScanByPathsService.scan(root, ["domain/*"], cfg, cfg.list_scan)
    assert [f.path for f in res.files] == ["domain/a.py", "domain/sub/b.py"]


def test_case_14_missing_file_fail_fast(tmp_path: Path) -> None:
    """
    14. `no_such_file.py` → missing (fail-fast), скан не стартует.
    """
    root = _mk_proj(tmp_path)
    (root / "a.txt").write_text("x\n", encoding="utf-8")

    cfg = Config()
    with pytest.raises(ListScanValidationError) as e:
        ScanByPathsService.scan(root, ["no_such_file.py"], cfg, cfg.list_scan)

    diag = e.value.diagnostics
    missing = _get_group(diag, "missing")
    _assert_single_item(missing, value="no_such_file.py")


def test_case_14a_dir_token_domain_first_level_only(tmp_path: Path) -> None:
    """
    14a. `domain` (явная директория без wildcard) → только файлы первого уровня внутри domain.
    """
    root = _mk_proj(tmp_path)
    (root / "domain").mkdir()
    (root / "domain" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (root / "domain" / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "domain" / "sub").mkdir()
    (root / "domain" / "sub" / "b.py").write_text("print('b')\n", encoding="utf-8")

    cfg = Config()
    res = ScanByPathsService.scan(root, ["domain"], cfg, cfg.list_scan)
    assert [f.path for f in res.files] == ["domain/a.py", "domain/a.txt"]


def test_case_14b_dir_token_domain_with_trailing_slash_same_as_domain(tmp_path: Path) -> None:
    """
    14b. `domain/` → то же, что и `domain`.
    """
    root = _mk_proj(tmp_path)
    (root / "domain").mkdir()
    (root / "domain" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (root / "domain" / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "domain" / "sub").mkdir()
    (root / "domain" / "sub" / "b.py").write_text("print('b')\n", encoding="utf-8")

    cfg = Config()
    res = ScanByPathsService.scan(root, ["domain/"], cfg, cfg.list_scan)
    assert [f.path for f in res.files] == ["domain/a.py", "domain/a.txt"]


def test_case_15_zero_matches_fail_fast(tmp_path: Path) -> None:
    """
    15. `bad_pattern_zzz/*` → zero_matches (fail-fast), причина no_matches.
    """
    root = _mk_proj(tmp_path)
    (root / "a.txt").write_text("x\n", encoding="utf-8")

    cfg = Config()
    with pytest.raises(ListScanValidationError) as e:
        ScanByPathsService.scan(root, ["bad_pattern_zzz/*"], cfg, cfg.list_scan)

    diag = e.value.diagnostics
    zm = _get_group(diag, "zero_matches")
    _assert_single_item(zm, value="bad_pattern_zzz/*", reason="no_matches")


def test_case_16_multiple_errors_grouped_and_deduped_with_multiplier(tmp_path: Path) -> None:
    """
    16. Несколько ошибок сразу → группы Missing / 0 matches / Bad pattern syntax,
        элементы дедуплицируются, но показывается ×N (count).
    """
    root = _mk_proj(tmp_path)
    (root / "src").mkdir()
    (root / "src" / "ok.txt").write_text("ok\n", encoding="utf-8")

    cfg = Config()
    tokens = [
        "no_such_file.py",
        "no_such_file.py",
        "bad_pattern_zzz/*",
        "bad_pattern_zzz/*",
        "src/[abc",  # плохой синтаксис []
        "src/[abc",
    ]

    with pytest.raises(ListScanValidationError) as e:
        ScanByPathsService.scan(root, tokens, cfg, cfg.list_scan)

    diag = e.value.diagnostics
    assert [g.kind for g in diag.groups] == ["missing", "zero_matches", "bad_pattern_syntax"]

    missing = _get_group(diag, "missing")
    assert [(it.value, it.count) for it in missing.items] == [("no_such_file.py", 2)]

    zm = _get_group(diag, "zero_matches")
    assert [(it.value, it.count, it.reason) for it in zm.items] == [("bad_pattern_zzz/*", 2, "no_matches")]

    bad = _get_group(diag, "bad_pattern_syntax")
    assert [(it.value, it.count) for it in bad.items] == [("src/[abc", 2)]


def test_case_17_ignore_filters_disables_ignore_hidden_dirs_files(tmp_path: Path) -> None:
    """
    17. “Игнорировать фильтры”:
      - скрытые файлы включаются
      - ignore_dirs и ignore_files не применяются
    (бинарность/max_file_size тут не проверяем).
    """
    root = _mk_proj(tmp_path)
    (root / "sub").mkdir()

    (root / "visible.txt").write_text("ok\n", encoding="utf-8")
    (root / ".hidden.txt").write_text("hidden\n", encoding="utf-8")
    (root / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    (root / "sub" / "in_sub.txt").write_text("sub\n", encoding="utf-8")

    cfg = Config()
    # подложим свои фильтры
    cfg.ignore_hidden = True
    cfg.ignore_files = cfg.ignore_files + ("ignored.txt",)
    cfg.ignore_dirs = cfg.ignore_dirs + ("sub",)

    tokens = ["visible.txt", ".hidden.txt", "ignored.txt", "sub/in_sub.txt"]

    # ignore_filters=false → применяются фильтры
    cfg.list_scan.ignore_filters = False
    res_filtered = ScanByPathsService.scan(root, tokens, cfg, cfg.list_scan)
    assert [f.path for f in res_filtered.files] == ["visible.txt"]

    # ignore_filters=true → фильтры отключены
    cfg.list_scan.ignore_filters = True
    res_all = ScanByPathsService.scan(root, tokens, cfg, cfg.list_scan)
    assert [f.path for f in res_all.files] == [".hidden.txt", "ignored.txt", "sub/in_sub.txt", "visible.txt"]


def test_case_17_env_policy_include_env_false_is_missing(tmp_path: Path) -> None:
    """
    17 (.env). include_env=false и .env явно запрошен → missing (fail-fast) с причиной "Файл скрыт настройками."
    (Тест допускает старую формулировку, если она у тебя уже зафиксирована кодом.)
    """
    root = _mk_proj(tmp_path)
    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")

    cfg = Config(include_env=False)
    with pytest.raises(ListScanValidationError) as e:
        ScanByPathsService.scan(root, [".env"], cfg, cfg.list_scan)

    diag = e.value.diagnostics
    missing = _get_group(diag, "missing")
    _assert_single_item(missing, value=".env")

    detail = missing.items[0].detail
    assert detail is not None
    assert detail in ("Файл скрыт настройками.", "скрыт настройками")


def test_case_17_env_policy_include_env_true_includes_env(tmp_path: Path) -> None:
    """
    17 (.env). include_env=true и .env явно запрошен → включается.
    """
    root = _mk_proj(tmp_path)
    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")

    cfg = Config(include_env=True)
    res = ScanByPathsService.scan(root, [".env"], cfg, cfg.list_scan)
    assert [f.path for f in res.files] == [".env"]


def test_case_18_matched_but_filtered_out_is_zero_matches_filtered_out(tmp_path: Path) -> None:
    """
    18. Паттерн совпадает, но всё скрыто фильтрами → zero_matches с reason=filtered_out.
    """
    root = _mk_proj(tmp_path)
    (root / "a.py").write_text("print('a')\n", encoding="utf-8")

    cfg = Config()
    cfg.ignore_files = cfg.ignore_files + ("*.py",)
    cfg.list_scan.ignore_filters = False

    with pytest.raises(ListScanValidationError) as e:
        ScanByPathsService.scan(root, ["*.py"], cfg, cfg.list_scan)

    diag = e.value.diagnostics
    zm = _get_group(diag, "zero_matches")
    _assert_single_item(zm, value="*.py", reason="filtered_out")


def test_case_19_pattern_matched_only_dirs_and_expand_dir_match_false_is_zero_matches(tmp_path: Path) -> None:
    """
    19. Паттерн совпал только с директориями и expand_dir_match=false → zero_matches (no_matches).
    """
    root = _mk_proj(tmp_path)
    (root / "domain").mkdir()
    (root / "domain" / "sub").mkdir()
    (root / "domain" / "sub" / "deep.txt").write_text("x\n", encoding="utf-8")

    cfg = Config()
    cfg.list_scan.expand_dir_match = False

    with pytest.raises(ListScanValidationError) as e:
        ScanByPathsService.scan(root, ["domain/*"], cfg, cfg.list_scan)

    diag = e.value.diagnostics
    zm = _get_group(diag, "zero_matches")
    _assert_single_item(zm, value="domain/*", reason="no_matches")
