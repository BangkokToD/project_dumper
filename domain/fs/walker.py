from __future__ import annotations

import threading
from pathlib import Path
import queue

from domain.fs.rules import is_ignored_dir, is_ignored_file
from domain.models import ScanOptions
from infrastructure import filesystem
from infrastructure.gitignore_cache import GitignoreCache
from config.model import Config
from config import storage


class Walker:
    """
    Обходчик проекта.

    Семантика collapsed:
    - в дереве папка отображается, но содержимое заменяется на "…";
    - при ignore_collapsed папка раскрывается только для текущего скана.
    """

    def __init__(self) -> None:
        self.cfg = Config()
        self.git = GitignoreCache()

    def load_cfg(self, root: Path) -> None:
        self.cfg = storage.load()
        self.git.build(root)

    def skip_dir(self, path: Path) -> bool:
        return is_ignored_dir(path, self.cfg, self.git)

    def skip_file(self, path: Path) -> bool:
        return is_ignored_file(path, self.cfg, self.git)

    def list_entries(self, dir_path: Path) -> list[Path]:
        entries = [
            p
            for p in filesystem.iterdir(dir_path)
            if (self.cfg.follow_symlinks or not p.is_symlink())
        ]
        out: list[Path] = []
        for p in entries:
            if p.is_dir():
                if self.skip_dir(p):
                    continue
            else:
                if self.skip_file(p):
                    continue
            out.append(p)

        def key(p: Path) -> tuple[int, str]:
            return (0 if (self.cfg.dirs_first_in_tree and p.is_dir()) else 1, p.name.lower())

        return sorted(out, key=key)

    def build_tree(self, root: Path, options: ScanOptions | None = None) -> str:
        """
        Построить дерево проекта.

        Правила:
        - collapsed: папка видна, содержимое заменяется на "…";
        - ignore_collapsed: collapsed игнорируется только для текущего скана;
        - если директория пуста после фильтров -> "…".
        """
        options = options or ScanOptions()
        collapsed = options.collapsed_dirs
        excluded = options.excluded_files

        # В режиме "игнорировать" показываем файлы, скрытые вручную (excluded_files)
        if options.ignore_manual_excluded:
            excluded = set()
        # Режим "игнорировать сворачивание": collapsed не влияет на построение дерева.
        if options.ignore_collapsed:
            collapsed = set()


        lines: list[str] = []

        def rec(cur: Path, prefix: str = "") -> None:
            all_entries = self.list_entries(cur)
            entries = [e for e in all_entries if not (e.is_file() and e in excluded)]

            # Пустая папка после фильтров: всегда "…"
            if not entries:
                lines.append(prefix + "…")
                return

            for i, p in enumerate(entries):
                last = i == (len(entries) - 1)
                branch = "└── " if last else "├── "
                lines.append(prefix + branch + p.name)
                if p.is_dir():
                    ext = prefix + ("    " if last else "│   ")
                    # Collapsed: папка видна, но содержимое заменяем на "…".
                    if p in collapsed:
                        lines.append(ext + "…")
                        continue
                    rec(p, ext)

        lines.append(root.name + "/")
        rec(root)
        return "\n".join(lines)

    def iter_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for dirpath, dirnames, filenames in filesystem.walk(
            root, followlinks=self.cfg.follow_symlinks
        ):
            d = Path(dirpath)
            dirnames[:] = [n for n in dirnames if not self.skip_dir(d / n)]
            for f in filenames:
                p = d / f
                if not self.skip_file(p):
                    files.append(p)
        files.sort(key=lambda p: p.relative_to(root).as_posix().lower())
        return files


class ScanThread(threading.Thread):
    """
    Фоновый воркер сканирования (временно совместимый с текущим UI).
    """

    def __init__(
        self,
        root: Path,
        walker: Walker,
        queue_out: "queue.Queue[tuple[str, object]]",
        collapsed_dirs: set[Path],
        excluded_files: set[Path],
        mode,
        ignore_collapsed: bool,
        ignore_manual_excluded: bool,
    ):
        super().__init__(daemon=True)
        self.root = root
        self.w = walker
        self.q = queue_out
        self.collapsed = collapsed_dirs
        self.excluded = excluded_files
        self.mode = mode
        self.ignore_collapsed = ignore_collapsed
        self.ignore_manual_excluded = ignore_manual_excluded

    def run(self) -> None:
        try:
            # конфиг, как и раньше, берём через load_cfg
            self.w.load_cfg(self.root)

            opts = ScanOptions(
                mode=self.mode,
                collapsed_dirs=set(self.collapsed),
                excluded_files=set(self.excluded),
                ignore_collapsed=bool(self.ignore_collapsed),
                ignore_manual_excluded=bool(self.ignore_manual_excluded),
            )

            from services.scan_service import ScanService

            res = ScanService.scan(self.root, self.w.cfg, opts)
            self.q.put(("tree", res.tree or ""))

            total = len(res.files)
            self.q.put(("total", total))

            for i, f in enumerate(res.files, 1):
                self.q.put(("file_header", f.path))
                if f.content is None:
                    self.q.put(("file_skipped", f.skipped_reason or ""))
                else:
                    self.q.put(("file_chunk", f.content))
                self.q.put(("file_sep", None))
                self.q.put(("progress", i))

            self.q.put(("done", None))

        except Exception as e:
            self.q.put(("error", str(e)))
