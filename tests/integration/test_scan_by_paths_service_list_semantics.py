from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.model import Config
from services.scan_by_paths_service import ScanByPathsService


@dataclass(slots=True)
class LS:
    star_is_recursive: bool
    expand_dir_match: bool
    ignore_filters: bool = False



def _mk_proj(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()

    # корневой py
    (root / "top.py").write_text("print('top')\n", encoding="utf-8")

    # domain с файлами 1-го уровня + поддир
    (root / "domain" / "sub").mkdir(parents=True)
    (root / "domain" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (root / "domain" / "a.txt").write_text("txt\n", encoding="utf-8")
    (root / "domain" / "sub" / "b.py").write_text("print('b')\n", encoding="utf-8")

    # директория для expand_dir_match: матчится в dir без файлов 1-го уровня
    (root / "empty_first" / "sub" / "deep").mkdir(parents=True)
    (root / "empty_first" / "sub" / "deep" / "x.py").write_text("print('x')\n", encoding="utf-8")

    # директория для expand_dir_match: матчится в dir с файлами 1-го уровня
    (root / "match_dir" / "inner" / "deep").mkdir(parents=True)
    (root / "match_dir" / "inner" / "f1.txt").write_text("f1\n", encoding="utf-8")
    (root / "match_dir" / "inner" / "deep" / "z.py").write_text("print('z')\n", encoding="utf-8")

    return root


def test_star_is_recursive_transforms_single_star(tmp_path: Path) -> None:
    root = _mk_proj(tmp_path)
    cfg = Config()

    # star_is_recursive выключен: *.py только в корне
    r1 = ScanByPathsService.scan(root, ["*.py"], cfg, LS(star_is_recursive=False, expand_dir_match=False))
    assert [f.path for f in r1.files] == ["top.py"]

    # star_is_recursive включен: *.py рекурсивно
    r2 = ScanByPathsService.scan(root, ["*.py"], cfg, LS(star_is_recursive=True, expand_dir_match=False))
    assert [f.path for f in r2.files] == ["domain/a.py", "domain/sub/b.py", "empty_first/sub/deep/x.py", "match_dir/inner/deep/z.py", "top.py"]


def test_dir_token_includes_only_first_level_files(tmp_path: Path) -> None:
    root = _mk_proj(tmp_path)
    cfg = Config()

    # даже при star_is_recursive=True: явная директория -> только 1-й уровень (14a/14b)
    r1 = ScanByPathsService.scan(root, ["domain"], cfg, LS(star_is_recursive=True, expand_dir_match=False))
    assert [f.path for f in r1.files] == ["domain/a.py", "domain/a.txt"]

    r2 = ScanByPathsService.scan(root, ["domain/"], cfg, LS(star_is_recursive=True, expand_dir_match=False))
    assert [f.path for f in r2.files] == ["domain/a.py", "domain/a.txt"]


def test_expand_dir_match_first_level_when_files_exist(tmp_path: Path) -> None:
    root = _mk_proj(tmp_path)
    cfg = Config()

    # match_dir/* матчится в директорию match_dir/inner
    # expand_dir_match=True и star_is_recursive=False -> только файлы 1-го уровня (без deep/z.py)
    r = ScanByPathsService.scan(root, ["match_dir/*"], cfg, LS(star_is_recursive=False, expand_dir_match=True))
    assert [f.path for f in r.files] == ["match_dir/inner/f1.txt"]


def test_expand_dir_match_rule_731_when_no_first_level_files(tmp_path: Path) -> None:
    root = _mk_proj(tmp_path)
    cfg = Config()

    # empty_first/* матчится в директорию empty_first/sub,
    # но в ней нет файлов 1-го уровня -> правило 7.3.1: рекурсивно даже при star_is_recursive=False
    r = ScanByPathsService.scan(root, ["empty_first/*"], cfg, LS(star_is_recursive=False, expand_dir_match=True))
    assert [f.path for f in r.files] == ["empty_first/sub/deep/x.py"]
