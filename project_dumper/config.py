from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal
from pathlib import Path
import json

RC_PATH = Path.home() / ".project_dumper.json"

@dataclass(slots=True)
class Config:
    ignore_hidden: bool = True
    max_file_size: int = 512 * 1024
    encoding: str = "utf-8"
    errors_policy: str = "replace"
    follow_symlinks: bool = False
    ignore_dirs: tuple[str, ...] = (
        ".git","__pycache__","node_modules",".venv","venv",".idea",".vscode",
        ".mypy_cache",".pytest_cache",".tox","build","dist","target",".cache",
    )
    ignore_files: tuple[str, ...] = (
        ".gitignore","*.png","*.jpg","*.jpeg","*.gif","*.webp","*.ico",
        "*.pdf","*.zip","*.tar","*.gz","*.7z","*.rar",
        "*.mp3","*.wav","*.ogg","*.flac",
        "*.mov","*.mp4","*.avi","*.mkv",
        "*.exe","*.dll","*.so","*.bin",
        "*.otf","*.ttf","*.woff","*.woff2",
        "*.pyc","*.pyo","*.class","*.o","*.a","*.dylib",
        "*.sqlite*","*.db",
    )
    dirs_first_in_tree: bool = True
    binary_threshold: float = 0.30
    detect_encoding: bool = True
    output_format: str = "txt"  # txt|md|json
    theme: Literal["light", "dark"] = "light"        # light|dark
    include_collapsed_in_dump: bool = True

    # Diff settings
    # Модификатор, который должен быть зажат для копирования группы строк
    # с одинаковым знаком (+/-). Допустимые значения: "Ctrl", "Shift",
    # "Alt", "Ctrl+Shift".
    diff_group_modifier: str = "Ctrl"
    # Длительность анимации подсветки копируемых строк (мс).
    diff_copy_flash_duration_ms: int = 300

def load_defaults() -> Config:
    if RC_PATH.exists():
        try:
            data: dict[str, object] = json.loads(RC_PATH.read_text(encoding="utf-8"))
            cfg = Config()
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, tuple(v) if k in ("ignore_dirs","ignore_files") else v)
            return cfg
        except Exception:
            pass
    return Config()

def save_defaults(cfg: Config) -> None:
    RC_PATH.write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
