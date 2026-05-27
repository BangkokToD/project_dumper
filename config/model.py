from __future__ import annotations

from dataclasses import dataclass, asdict, field

from enum import Enum
from typing import Any, Literal


class Theme(str, Enum):
    """Тема приложения."""

    LIGHT = "light"
    DARK = "dark"


class OutputFormat(str, Enum):
    """Формат вывода дампа."""

    TXT = "txt"
    MD = "md"
    JSON = "json"


def _to_bool(value: Any, default: bool) -> bool:
    """Нормализация bool-значений для конфигурации."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"1", "true", "yes", "on"}:
            return True
        if s in {"0", "false", "no", "off"}:
            return False
    return default


@dataclass(slots=True)
class ListScanConfig:
    """Namespace list_scan.* (вкладка "Список")."""

    star_is_recursive: bool = False
    ignore_filters: bool = False
    expand_dir_match: bool = False

    def normalize(self) -> "ListScanConfig":
        self.star_is_recursive = _to_bool(self.star_is_recursive, False)
        self.ignore_filters = _to_bool(self.ignore_filters, False)
        self.expand_dir_match = _to_bool(self.expand_dir_match, False)
        return self


@dataclass(slots=True)
class TextCleanerConfig:
    """Namespace text_cleaner.* (вкладка "Текст")."""

    preserve_separator_spacing: bool = True

    def normalize(self) -> "TextCleanerConfig":
        self.preserve_separator_spacing = _to_bool(self.preserve_separator_spacing, True)
        return self


@dataclass(slots=True)
class Config:
    """
    Модель конфигурации приложения.
    """

    ignore_hidden: bool = True
    include_env: bool = False
    max_file_size: int = 512 * 1024
    encoding: str = "utf-8"
    errors_policy: str = "replace"
    follow_symlinks: bool = False
    ignore_dirs: tuple[str, ...] = (
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".idea",
        ".vscode",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        "build",
        "dist",
        "target",
        ".cache",
    )
    ignore_files: tuple[str, ...] = (
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.webp",
        "*.ico",
        "*.pdf",
        "*.zip",
        "*.tar",
        "*.gz",
        "*.7z",
        "*.rar",
        "*.mp3",
        "*.wav",
        "*.ogg",
        "*.flac",
        "*.mov",
        "*.mp4",
        "*.avi",
        "*.mkv",
        "*.exe",
        "*.dll",
        "*.so",
        "*.bin",
        "*.otf",
        "*.ttf",
        "*.woff",
        "*.woff2",
        "*.pyc",
        "*.pyo",
        "*.class",
        "*.o",
        "*.a",
        "*.dylib",
        "*.sqlite*",
        "*.db",
    )
    dirs_first_in_tree: bool = True
    binary_threshold: float = 0.30
    detect_encoding: bool = True
    output_format: str = "md"  # md|txt|json (пока оставляем строкой для совместимости)
    theme: Literal["light", "dark"] = "light"

    # Diff settings
    diff_group_modifier: str = "Ctrl"
    diff_copy_flash_duration_ms: int = 300

    # list_scan namespace (v0.3.0)
    list_scan: ListScanConfig = field(default_factory=ListScanConfig)

    # text_cleaner namespace
    text_cleaner: TextCleanerConfig = field(default_factory=TextCleanerConfig)

    def normalize(self) -> "Config":
        """
        Нормализовать конфиг (включая старые значения).
        """
        self.include_env = _to_bool(self.include_env, False)
        if self.max_file_size < 0:
            self.max_file_size = 0
        if not (0.0 <= float(self.binary_threshold) <= 1.0):
            self.binary_threshold = 0.30
        if not self.encoding:
            self.encoding = "utf-8"
        if self.errors_policy not in {"strict", "replace", "ignore"}:
            self.errors_policy = "replace"
        if self.output_format not in {"txt", "md", "json"}:
            self.output_format = "md"
        if self.theme not in {"light", "dark"}:
            self.theme = "light"
        if self.diff_copy_flash_duration_ms < 50:
            self.diff_copy_flash_duration_ms = 300
        if self.diff_group_modifier not in {"Ctrl", "Shift", "Alt", "Ctrl+Shift"}:
            self.diff_group_modifier = "Ctrl"

        # list_scan: если битый тип — восстанавливаем дефолты/мигрируем dict
        if isinstance(self.list_scan, dict):
            ls = ListScanConfig()
            for k, v in self.list_scan.items():
                if hasattr(ls, k):
                    setattr(ls, k, v)
            self.list_scan = ls
        elif not isinstance(self.list_scan, ListScanConfig):
            self.list_scan = ListScanConfig()
        self.list_scan.normalize()

        # text_cleaner: если битый тип — восстанавливаем дефолты/мигрируем dict
        if isinstance(self.text_cleaner, dict):
            tc = TextCleanerConfig()
            for k, v in self.text_cleaner.items():
                if hasattr(tc, k):
                    setattr(tc, k, v)
            self.text_cleaner = tc
        elif not isinstance(self.text_cleaner, TextCleanerConfig):
            self.text_cleaner = TextCleanerConfig()
        self.text_cleaner.normalize()

        return self


def to_dict(cfg: Config) -> dict[str, Any]:
    """Сериализовать Config в dict."""
    return asdict(cfg)


def _apply_list_scan_dict(ls: ListScanConfig, data: dict[str, Any]) -> ListScanConfig:
    # функция должна быть чистой: работает ТОЛЬКО с ls и nested dict.
    # dotted keys обрабатываются в apply_dict(cfg, data)
    if not isinstance(ls, ListScanConfig):
        ls = ListScanConfig()
    if not isinstance(data, dict):
        return ls.normalize()

    for k, v in data.items():
        if hasattr(ls, k):
            setattr(ls, k, v)

    return ls.normalize()


def _apply_text_cleaner_dict(
    tc: TextCleanerConfig,
    data: dict[str, Any],
) -> TextCleanerConfig:
    # функция должна быть чистой: работает ТОЛЬКО с tc и nested dict.
    # dotted keys обрабатываются в apply_dict(cfg, data)
    if not isinstance(tc, TextCleanerConfig):
        tc = TextCleanerConfig()
    if not isinstance(data, dict):
        return tc.normalize()

    for k, v in data.items():
        if hasattr(tc, k):
            setattr(tc, k, v)

    return tc.normalize()




def apply_dict(cfg: Config, data: dict[str, Any]) -> Config:
    """
    Применить dict к Config (с защитой от некорректных значений).
    """
    for k, v in data.items():
        # list_scan: поддерживаем как вложенный dict, так и dotted keys
        if k == "list_scan":
            if isinstance(v, dict):
                cfg.list_scan = _apply_list_scan_dict(cfg.list_scan, v)
            else:
                cfg.list_scan = ListScanConfig()
            continue
        if isinstance(k, str) and k.startswith("list_scan."):
            sub = k.split(".", 1)[1]
            if hasattr(cfg.list_scan, sub):
                setattr(cfg.list_scan, sub, v)
            continue

        # text_cleaner: поддерживаем как вложенный dict, так и dotted keys
        if k == "text_cleaner":
            if isinstance(v, dict):
                cfg.text_cleaner = _apply_text_cleaner_dict(cfg.text_cleaner, v)
            else:
                cfg.text_cleaner = TextCleanerConfig()
            continue
        if isinstance(k, str) and k.startswith("text_cleaner."):
            sub = k.split(".", 1)[1]
            if hasattr(cfg.text_cleaner, sub):
                setattr(cfg.text_cleaner, sub, v)
            continue


        if not hasattr(cfg, k):
            continue
        if k in ("ignore_dirs", "ignore_files"):
            try:
                setattr(cfg, k, tuple(v))
            except Exception:
                # если сломано/не список — игнорируем
                continue
        else:
            setattr(cfg, k, v)
    return cfg.normalize()
