from __future__ import annotations

from pathlib import Path

from project_dumper.config import Config, RC_PATH, load_defaults, save_defaults


def test_config_roundtrip(tmp_path: Path, monkeypatch) -> None:
    # сохраняем в временный RC-файл и загружаем обратно
    rc = tmp_path / ".project_dumper.json"
    monkeypatch.setattr("project_dumper.config.RC_PATH", rc, raising=True)

    cfg = Config()
    cfg.ignore_hidden = False
    cfg.max_file_size = 12345
    cfg.theme = "dark"
    cfg.diff_group_modifier = "Shift"
    cfg.diff_copy_flash_duration_ms = 777

    save_defaults(cfg)

    assert rc.exists()

    loaded = load_defaults()
    assert loaded.ignore_hidden is False
    assert loaded.max_file_size == 12345
    assert loaded.theme == "dark"
    assert loaded.diff_group_modifier == "Shift"
    assert loaded.diff_copy_flash_duration_ms == 777


def test_load_defaults_on_broken_file(tmp_path: Path, monkeypatch) -> None:
    # Если RC-файл битый, load_defaults должен вернуть конфиг по умолчанию
    rc = tmp_path / ".project_dumper.json"
    monkeypatch.setattr("project_dumper.config.RC_PATH", rc, raising=True)

    rc.write_text("{ this is not valid json", encoding="utf-8")

    cfg = load_defaults()
    assert isinstance(cfg, Config)
    # проверяем, что подставлены дефолты
    assert cfg.ignore_hidden is True
    assert cfg.theme == "light"


def test_rc_path_constant_is_path() -> None:
    # просто sanity-check, что RC_PATH выглядит как файл в HOME
    assert isinstance(RC_PATH, Path)
    assert ".project_dumper.json" in RC_PATH.name
