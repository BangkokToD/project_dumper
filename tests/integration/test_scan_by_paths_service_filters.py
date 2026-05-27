from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pytest

from config.model import Config
from services.scan_by_paths_service import ScanByPathsService
from domain.list_scan.diagnostics import ListScanValidationError


@dataclass(slots=True)
class LS:
    star_is_recursive: bool = False
    expand_dir_match: bool = False
    ignore_filters: bool = False


def _mk_proj(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()

    # .gitignore скрывает ignored.txt, ignored_dir/ и даже .env (но include_env=true должен пробивать)
    (root / ".gitignore").write_text("ignored.txt\nignored_dir/\n.env\n", encoding="utf-8")

    (root / "kept.txt").write_text("kept\n", encoding="utf-8")
    (root / "ignored.txt").write_text("ignored\n", encoding="utf-8")

    (root / "ignored_dir").mkdir()
    (root / "ignored_dir" / "in.txt").write_text("in\n", encoding="utf-8")

    (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (root / ".env.example").write_text("SECRET=example\n", encoding="utf-8")

    return root


def test_ignore_filters_false_applies_gitignore_and_ignore_dirs(tmp_path: Path) -> None:
    root = _mk_proj(tmp_path)
    cfg = Config()  # ignore_hidden=True, include_env=False

    r = ScanByPathsService.scan(
        root,
        ["kept.txt", "ignored.txt", ".gitignore", "ignored_dir/in.txt"],
        cfg,
        LS(ignore_filters=False),
    )

    # ignored.txt и ignored_dir/* убираются .gitignore (и/или ignore_dirs), но .gitignore остаётся видимым
    assert [f.path for f in r.files] == [".gitignore", "kept.txt"]


def test_ignore_filters_true_disables_gitignore_and_other_filters(tmp_path: Path) -> None:
    root = _mk_proj(tmp_path)
    cfg = Config()  # include_env=False

    r = ScanByPathsService.scan(
        root,
        ["kept.txt", "ignored.txt", ".gitignore", "ignored_dir/in.txt"],
        cfg,
        LS(ignore_filters=True),
    )

    # фильтры отключены -> всё, кроме .env (security-policy), попадает
    assert [f.path for f in r.files] == [".gitignore", "ignored.txt", "ignored_dir/in.txt", "kept.txt"]


def test_env_security_rule_applies_even_when_ignore_filters_true(tmp_path: Path) -> None:
    root = _mk_proj(tmp_path)
    cfg = Config()  # include_env=False

    with pytest.raises(ListScanValidationError) as e:
        ScanByPathsService.scan(root, [".env", ".env.example"], cfg, LS(ignore_filters=True))

    diag = e.value.diagnostics
    assert [g.kind for g in diag.groups] == ["hidden"]
    assert [(it.value, it.count, it.detail) for it in diag.groups[0].items] == [(".env", 1, "скрыт настройками")]



def test_env_allowed_when_include_env_true_even_if_gitignore_mentions_env(tmp_path: Path) -> None:
    root = _mk_proj(tmp_path)
    cfg = Config(include_env=True)

    r = ScanByPathsService.scan(root, [".env"], cfg, LS(ignore_filters=False))
    assert [f.path for f in r.files] == [".env"]
