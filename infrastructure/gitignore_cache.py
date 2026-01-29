from __future__ import annotations
from pathlib import Path
from typing import Optional

try:
    from pathspec import PathSpec
except Exception:
    PathSpec = None

class GitignoreCache:
    def __init__(self) -> None:
        self.root: Optional[Path] = None
        self.spec: Optional[PathSpec] = None
        # Снапшот состояния .gitignore файлов.
        # Храним (mtime_ns, size), чтобы не зависеть от низкой точности mtime в CI/FS.
        self._snapshot: dict[Path, tuple[int, int]] = {}

    def _collect_gitignores(self, root: Path) -> list[Path]:
        out = []
        for p in root.rglob(".gitignore"):
            out.append(p)
        return out

    def _changed(self, files: list[Path]) -> bool:
        cur: dict[Path, tuple[int, int]] = {}
        for p in files:
            st = p.stat()
            # mtime_ns даёт максимальную доступную точность, size страхует от совпадений по времени
            cur[p] = (int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))), int(st.st_size))
        if cur != self._snapshot:
            self._snapshot = cur
            return True
        return False

    def build(self, root: Path) -> None:
        if not PathSpec:
            self.root, self.spec = root, None
            return
        gi_files = self._collect_gitignores(root)
        # всегда обновляем снапшот и узнаём, менялся ли набор .gitignore
        changed = self._changed(gi_files)
        if self.root != root or changed:
            lines: list[str] = []
            for gi in gi_files:
                base_rel = gi.parent.relative_to(root).as_posix() if gi.parent != root else ""
                for raw in gi.read_text(encoding="utf-8", errors="ignore").splitlines():
                    s = raw.strip()
                    if not s or s.startswith("#"):
                        continue
                    neg = s.startswith("!")
                    pat = s[1:] if neg else s
                    pat2 = pat.lstrip("/") if pat.startswith("/") else pat
                    if base_rel:
                        pat2 = f"{base_rel}/{pat2}"
                    norm = "/".join(seg for seg in pat2.split("/") if seg != ".")
                    lines.append(("!" if neg else "") + norm)
            self.root = root
            self.spec = PathSpec.from_lines("gitwildmatch", lines) if lines else None

    def ignored(self, path: Path) -> bool:
        if not PathSpec or not self.root or not self.spec:
            return False
        rel = path.resolve().relative_to(self.root.resolve()).as_posix()
        if path.is_dir() and not rel.endswith("/"):
            rel += "/"
        return bool(self.spec.match_file(rel))
