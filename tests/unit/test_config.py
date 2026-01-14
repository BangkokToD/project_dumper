from __future__ import annotations

from pathlib import Path

from config import storage
from project_dumper.config import Config, load_defaults, save_defaults


def test_config_roundtrip(tmp_path: Path, monkeypatch) -> None:
    # сохраняем в portable рядом с entry_dir и загружаем обратно
    entry_dir = tmp_path / "app"
    entry_dir.mkdir()
    cfg = Config()
    cfg.ignore_hidden = False
    cfg.max_file_size = 12345
    cfg.theme = "dark"
    cfg.diff_group_modifier = "Shift"
    cfg.diff_copy_flash_duration_ms = 777

    # save_defaults пишет в portable (рядом с entrypoint), поэтому подменяем entry_dir через storage.save
    storage.save(cfg, entry_dir=entry_dir)
    rc = storage.portable_path(entry_dir)
    assert rc.exists()

    loaded = storage.load(entry_dir=entry_dir, home_dir=tmp_path / "home")
    assert loaded.ignore_hidden is False
    assert loaded.max_file_size == 12345
    assert loaded.theme == "dark"
    assert loaded.diff_group_modifier == "Shift"
    assert loaded.diff_copy_flash_duration_ms == 777


def test_load_defaults_on_broken_file(tmp_path: Path, monkeypatch) -> None:
    # Если portable-конфиг битый, должен вернуться конфиг по умолчанию
    entry_dir = tmp_path / "app"
    entry_dir.mkdir()
    bad = storage.portable_path(entry_dir)
    bad.write_text("{ this is not valid json", encoding="utf-8")

    cfg = storage.load(entry_dir=entry_dir, home_dir=tmp_path / "home")
    assert isinstance(cfg, Config)
    # проверяем, что подставлены дефолты
    assert cfg.ignore_hidden is True
    assert cfg.theme == "light"


def test_storage_paths_are_paths(tmp_path: Path) -> None:
    entry_dir = tmp_path / "app"
    entry_dir.mkdir()
    p1 = storage.portable_path(entry_dir)
    p2 = storage.home_path(tmp_path / "home")
    assert isinstance(p1, Path)
    assert isinstance(p2, Path)
    assert p1.name == ".project_dumper.json"
    assert p2.name == ".project_dumper.json"
