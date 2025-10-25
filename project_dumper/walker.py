from __future__ import annotations
import os, fnmatch, threading, queue
from pathlib import Path
from typing import Iterable
from .config import Config, load_defaults
from .gitignore_cache import GitignoreCache

class Walker:
    def __init__(self) -> None:
        self.cfg = Config()
        self.git = GitignoreCache()

    def load_cfg(self, root: Path) -> None:
        self.cfg = load_defaults()
        self.git.build(root)

    def _is_hidden(self, p: Path) -> bool:
        return any(part.startswith(".") for part in p.parts)

    def _match_any(self, name: str, patterns: tuple[str, ...]) -> bool:
        return any(fnmatch.fnmatch(name, pat) for pat in patterns)

    def skip_dir(self, path: Path) -> bool:
        name = path.name
        if self.cfg.ignore_hidden and name.startswith("."):
            return True
        if name in self.cfg.ignore_dirs or self._match_any(name, self.cfg.ignore_dirs):
            return True
        if self.git.ignored(path):
            return True
        return False

    def skip_file(self, path: Path) -> bool:
        name = path.name
        if self.cfg.ignore_hidden and name.startswith("."):
            return True
        if self._match_any(name, self.cfg.ignore_files):
            return True
        if self.git.ignored(path):
            return True
        return False

    def list_entries(self, dir_path: Path) -> list[Path]:
        entries = [p for p in dir_path.iterdir() if (self.cfg.follow_symlinks or not p.is_symlink())]
        out = []
        for p in entries:
            if p.is_dir():
                if self.skip_dir(p): continue
            else:
                if self.skip_file(p): continue
            out.append(p)
        def key(p: Path):
            return (0 if (self.cfg.dirs_first_in_tree and p.is_dir()) else 1, p.name.lower())
        return sorted(out, key=key)

    def build_tree(self, root: Path, collapsed: set[Path] | None = None) -> str:
        collapsed = collapsed or set()
        lines: list[str] = []

        def rec(cur: Path, prefix: str = "") -> None:
            entries = self.list_entries(cur)
            for i, p in enumerate(entries):
                last = (i == len(entries) - 1)
                branch = "└── " if last else "├── "
                lines.append(prefix + branch + p.name)
                if p.is_dir():
                    ext = prefix + ("    " if last else "│   ")
                    if p in collapsed:
                        # папка свёрнута слева → показываем маркер содержимого
                        lines.append(ext + "…")
                    else:
                        rec(p, ext)

        lines.append(root.name + "/")
        rec(root)
        return "\n".join(lines)
        
    def iter_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(root, followlinks=self.cfg.follow_symlinks):
            d = Path(dirpath)
            dirnames[:] = [n for n in dirnames if not self.skip_dir(d / n)]
            for f in filenames:
                p = d / f
                if not self.skip_file(p):
                    files.append(p)
        files.sort(key=lambda p: p.relative_to(root).as_posix().lower())
        return files

# Фоновый воркер с прогрессом
class ScanThread(threading.Thread):
    def __init__(self, root: Path, walker: Walker, queue_out: "queue.Queue[tuple[str,object]]", collapsed_dirs: set[Path], only_tree: bool):
        super().__init__(daemon=True)
        self.root = root
        self.w = walker
        self.q = queue_out
        self.collapsed = collapsed_dirs
        self.only_tree = only_tree

    def run(self):
        try:
            self.w.load_cfg(self.root)
            tree = self.w.build_tree(self.root, self.collapsed)
            self.q.put(("tree", tree))
            if self.only_tree:
                self.q.put(("done", None))
                return
            files = self.w.iter_files(self.root)
            total = len(files)
            self.q.put(("total", total))
            from .reader import read_text_streaming
            for i, p in enumerate(files, 1):
                rel = p.relative_to(self.root).as_posix()
                hide = any((p.is_relative_to(d) for d in self.collapsed)) if hasattr(p, "is_relative_to") \
                       else any(str(p).startswith(str(d)) for d in self.collapsed)

                if hide and not self.w.cfg.include_collapsed_in_dump:
                    # полностью пропускаем: ни заголовка, ни "Содержимое скрыто", ни file_sep
                    self.q.put(("progress", i))
                    continue

                self.q.put(("file_header", rel))
                if hide:  # include_collapsed_in_dump == True
                    self.q.put(("file_skipped", "Содержимое скрыто"))
                else:
                    for chunk in read_text_streaming(p, self.w.cfg):
                        self.q.put(("file_chunk", chunk))
                self.q.put(("file_sep", None))
                self.q.put(("progress", i))
            self.q.put(("done", None))
        except Exception as e:
            self.q.put(("error", str(e)))
