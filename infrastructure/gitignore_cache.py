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
        self._snapshot: dict[Path, float] = {}

    def _collect_gitignores(self, root: Path) -> list[Path]:
        out = []
        for p in root.rglob(".gitignore"):
            out.append(p)
        return out

    def _changed(self, files: list[Path]) -> bool:
        cur = {p: p.stat().st_mtime for p in files}
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
                    if pat.startswith("/"):
                        pat2 = pat.lstrip("/")
                    else:
                        pat2 = (f"{base_rel}/{pat}" if base_rel else pat)
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
