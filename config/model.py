from __future__ import annotations

from dataclasses import dataclass, asdict
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
    output_format: str = "txt"  # txt|md|json (пока оставляем строкой для совместимости)
    theme: Literal["light", "dark"] = "light"

    # Diff settings
    diff_group_modifier: str = "Ctrl"
    diff_copy_flash_duration_ms: int = 300

    def normalize(self) -> "Config":
        """
        Нормализовать конфиг (включая старые значения).
        """
        if not isinstance(self.include_env, bool):
            if isinstance(self.include_env, str):
                s = self.include_env.strip().lower()
                if s in {"1", "true", "yes", "on"}:
                    self.include_env = True  # type: ignore[assignment]
                else:
                    self.include_env = False  # type: ignore[assignment]
            else:
                self.include_env = bool(self.include_env)  # type: ignore[assignment]
        if self.max_file_size < 0:
            self.max_file_size = 0
        if not (0.0 <= float(self.binary_threshold) <= 1.0):
            self.binary_threshold = 0.30
        if not self.encoding:
            self.encoding = "utf-8"
        if self.errors_policy not in {"strict", "replace", "ignore"}:
            self.errors_policy = "replace"
        if self.output_format not in {"txt", "md", "json"}:
            self.output_format = "txt"
        if self.theme not in {"light", "dark"}:
            self.theme = "light"
        if self.diff_copy_flash_duration_ms < 50:
            self.diff_copy_flash_duration_ms = 300
        if self.diff_group_modifier not in {"Ctrl", "Shift", "Alt", "Ctrl+Shift"}:
            self.diff_group_modifier = "Ctrl"
        return self


def to_dict(cfg: Config) -> dict[str, Any]:
    """Сериализовать Config в dict."""
    return asdict(cfg)


def apply_dict(cfg: Config, data: dict[str, Any]) -> Config:
    """
    Применить dict к Config (с защитой от некорректных значений).
    """
    for k, v in data.items():
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
