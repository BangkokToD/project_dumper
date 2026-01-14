from __future__ import annotations

import os
from pathlib import Path

from config import storage
from config.model import Config


def test_storage_prefers_portable(tmp_path: Path) -> None:
    entry_dir = tmp_path / "app"
    entry_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    portable = entry_dir / ".project_dumper.json"
    home = home_dir / ".project_dumper.json"

    portable.write_text('{"theme":"dark","max_file_size":123}', encoding="utf-8")
    home.write_text('{"theme":"light","max_file_size":999}', encoding="utf-8")

    cfg = storage.load(entry_dir=entry_dir, home_dir=home_dir)
    assert cfg.theme == "dark"
    assert cfg.max_file_size == 123


def test_storage_fallbacks_to_home_when_no_portable(tmp_path: Path) -> None:
    entry_dir = tmp_path / "app"
    entry_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    (home_dir / ".project_dumper.json").write_text('{"theme":"dark"}', encoding="utf-8")
    cfg = storage.load(entry_dir=entry_dir, home_dir=home_dir)
    assert cfg.theme == "dark"


def test_storage_import_home_to_portable_via_callback(tmp_path: Path) -> None:
    entry_dir = tmp_path / "app"
    entry_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    home = home_dir / ".project_dumper.json"
    home.write_text('{"theme":"dark","diff_group_modifier":"Shift"}', encoding="utf-8")

    def always_yes(dec) -> bool:
        assert dec.needs_import is True
        return True

    cfg = storage.load(entry_dir=entry_dir, home_dir=home_dir, import_prompt=always_yes)
    assert cfg.theme == "dark"
    assert cfg.diff_group_modifier == "Shift"
    assert (entry_dir / ".project_dumper.json").exists()


def test_storage_returns_defaults_when_no_configs(tmp_path: Path) -> None:
    entry_dir = tmp_path / "app"
    entry_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    cfg = storage.load(entry_dir=entry_dir, home_dir=home_dir)
    assert isinstance(cfg, Config)
    assert cfg.theme in ("light", "dark")


def test_storage_portable_only_ignores_home(tmp_path: Path, monkeypatch) -> None:
    entry_dir = tmp_path / "app"
    entry_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    # есть home-конфиг, но portable отсутствует
    (home_dir / ".project_dumper.json").write_text('{"theme":"dark"}', encoding="utf-8")

    monkeypatch.setenv("PROJECT_DUMPER_PORTABLE_ONLY", "1")
    monkeypatch.setenv("PROJECT_DUMPER_DEFAULT_THEME", "light")

    cfg = storage.load(entry_dir=entry_dir, home_dir=home_dir)
    # HOME игнорируется, берём дефолт + env theme
    assert cfg.theme == "light"
