from __future__ import annotations

from pathlib import Path

from config import storage
from config.model import Config, apply_dict



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

    cfg.list_scan.star_is_recursive = True
    cfg.list_scan.ignore_filters = True
    cfg.list_scan.expand_dir_match = True

    cfg.text_cleaner.preserve_separator_spacing = False
    storage.save(cfg, entry_dir=entry_dir)
    rc = storage.portable_path(entry_dir)
    assert rc.exists()

    loaded = storage.load(entry_dir=entry_dir, home_dir=tmp_path / "home")
    assert loaded.ignore_hidden is False
    assert loaded.max_file_size == 12345
    assert loaded.theme == "dark"
    assert loaded.diff_group_modifier == "Shift"
    assert loaded.diff_copy_flash_duration_ms == 777
    assert loaded.list_scan.star_is_recursive is True
    assert loaded.list_scan.ignore_filters is True
    assert loaded.list_scan.expand_dir_match is True
    assert loaded.text_cleaner.preserve_separator_spacing is False


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


def test_list_scan_defaults_and_normalization() -> None:
    # дефолты, если ключей нет
    cfg = apply_dict(Config(), {})
    assert cfg.list_scan.star_is_recursive is False
    assert cfg.list_scan.ignore_filters is False
    assert cfg.list_scan.expand_dir_match is False

    # поломанные типы должны нормализоваться
    cfg2 = apply_dict(
        Config(),
        {
            "list_scan": {
                "star_is_recursive": "true",
                "ignore_filters": "no",
                "expand_dir_match": 1,
            }
        },
    )
    assert cfg2.list_scan.star_is_recursive is True
    assert cfg2.list_scan.ignore_filters is False
    assert cfg2.list_scan.expand_dir_match is True

    # dotted-keys тоже допускаем
    cfg3 = apply_dict(
        Config(),
        {
            "list_scan.star_is_recursive": "1",
            "list_scan.ignore_filters": "0",
            "list_scan.expand_dir_match": True,
        },
    )
    assert cfg3.list_scan.star_is_recursive is True
    assert cfg3.list_scan.ignore_filters is False
    assert cfg3.list_scan.expand_dir_match is True


def test_text_cleaner_defaults_and_normalization() -> None:
    # дефолт, если ключей нет: старые конфиги без text_cleaner не должны ломаться
    cfg = apply_dict(Config(), {})
    assert cfg.text_cleaner.preserve_separator_spacing is True

    # битый namespace должен восстанавливаться в дефолт
    cfg_broken = apply_dict(Config(), {"text_cleaner": "broken"})
    assert cfg_broken.text_cleaner.preserve_separator_spacing is True

    # normalize() должен уметь мигрировать dict, если он оказался в Config напрямую
    cfg_migrated = Config()
    cfg_migrated.text_cleaner = {"preserve_separator_spacing": "false"}  # type: ignore[assignment]
    cfg_migrated.normalize()
    assert cfg_migrated.text_cleaner.preserve_separator_spacing is False

    cases = [
        ("true", True),
        ("false", False),
        ("1", True),
        ("0", False),
        ("yes", True),
        ("no", False),
        ("on", True),
        ("off", False),
    ]

    for raw, expected in cases:
        cfg_nested = apply_dict(
            Config(),
            {"text_cleaner": {"preserve_separator_spacing": raw}},
        )
        assert cfg_nested.text_cleaner.preserve_separator_spacing is expected

        cfg_dotted = apply_dict(
            Config(),
            {"text_cleaner.preserve_separator_spacing": raw},
        )
        assert cfg_dotted.text_cleaner.preserve_separator_spacing is expected
