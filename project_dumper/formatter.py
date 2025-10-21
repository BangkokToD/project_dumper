from __future__ import annotations
import io, json
from typing import Any

SEP = "====="

class DumpBuilder:
    def __init__(self, mode: str = "txt"):
        self.mode = mode
        if mode == "json":
            self.obj = {"tree": "", "files": []}
        else:
            self.buf = io.StringIO()

    def set_tree(self, tree: str):
        if self.mode == "json":
            self.obj["tree"] = tree
        elif self.mode == "md":
            self.buf.write("# Структура проекта\n\n```\n")
            self.buf.write(tree)
            self.buf.write("\n```\n\n")
        else:
            self.buf.write("Структура проекта\n\n")
            self.buf.write(tree)
            self.buf.write("\n\n")

    def start_file(self, relpath: str):
        if self.mode == "json":
            self._cur = {"path": relpath, "content": ""}
            self.obj["files"].append(self._cur)
        elif self.mode == "md":
            self.buf.write(f"## {relpath}\n\n")
        else:
            self.buf.write(relpath + "\n\n")

    def add_chunk(self, s: str):
        if self.mode == "json":
            self._cur["content"] += s
        else:
            self.buf.write(s)

    def end_file(self, is_last: bool):
        if self.mode in ("md","txt"):
            self.buf.write("\n\n")
            if not is_last:
                self.buf.write(SEP + "\n\n")

    def build(self) -> str:
        if self.mode == "json":
            return json.dumps(self.obj, ensure_ascii=False, indent=2)
        return self.buf.getvalue()
