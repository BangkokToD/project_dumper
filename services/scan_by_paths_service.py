from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from config.model import Config
from domain.fs.reader import read_text_streaming
from domain.list_scan.models import SelectedPath, resolve_selected_paths
from domain.models import DumpFile, ScanResult


@dataclass(slots=True)
class _Candidate:
    """
    Внутренний кандидат на чтение.
    - rel_posix используется для dedup/sort без resolve().
    """

    abs_path: Path
    rel_posix: str


class ScanByPathsService:
    """
    Use-case: сканирование по токенам/паттернам из вкладки "Список".

    Commit 6 (скелет пайплайна):
    - resolve SelectedPath (kind + bad pattern syntax)
    - match паттернов через root.glob()
    - собрать кандидатов (пока без фильтров/expand/семантик *)
    - dedup по relative posix (root/rel без resolve)
    - sort по relative posix
    - read через read_text_streaming
    - вернуть ScanResult(tree=None, files=[...])
    """

    @staticmethod
    def scan(
        root: Path,
        tokens: list[str],
        cfg: Config,
        list_scan_settings: object,
    ) -> ScanResult:
        # list_scan_settings пока не используется в этом коммите (семантика — следующий коммит).
        _ = list_scan_settings

        selected = resolve_selected_paths(root, tokens, follow_symlinks=cfg.follow_symlinks)

        # Минимальный fail-fast (только bad pattern syntax из Commit 5).
        bad = [s.raw for s in selected if s.kind == "pattern" and s.bad_pattern_syntax]
        if bad:
            raise ValueError("Bad pattern syntax: " + ", ".join(bad))

        candidates = ScanByPathsService._collect_candidates(root, selected)
        ordered = ScanByPathsService._dedup_and_sort(candidates)

        out_files: list[DumpFile] = []
        for c in ordered:
            content = "".join(read_text_streaming(c.abs_path, cfg))
            out_files.append(DumpFile(path=c.rel_posix, content=content, skipped_reason=None))

        return ScanResult(tree=None, files=out_files)

    @staticmethod
    def _collect_candidates(root: Path, selected: Iterable[SelectedPath]) -> list[_Candidate]:
        out: list[_Candidate] = []

        for s in selected:
            if s.kind == "file":
                rel = ScanByPathsService._to_rel_posix(root, s.resolved)
                if rel is not None:
                    out.append(_Candidate(abs_path=s.resolved, rel_posix=rel))
                continue

            if s.kind == "dir":
                # Скелет: берём файлы 1-го уровня. Полная семантика/рекурсивность — в следующем коммите.
                try:
                    for ch in s.resolved.iterdir():
                        if not ch.is_file():
                            continue
                        rel = ScanByPathsService._to_rel_posix(root, ch)
                        if rel is not None:
                            out.append(_Candidate(abs_path=ch, rel_posix=rel))
                except Exception:
                    pass
                continue

            if s.kind == "pattern":
                # Path.glob для паттернов относительно root.
                try:
                    for m in root.glob(s.raw):
                        if not m.is_file():
                            continue
                        rel = ScanByPathsService._to_rel_posix(root, m)
                        if rel is not None:
                            out.append(_Candidate(abs_path=m, rel_posix=rel))
                except Exception:
                    # Детальная диагностика будет отдельным коммитом.
                    pass
                continue

            # missing — в этом коммите просто игнорируем (fail-fast и причины — позже).

        return out

    @staticmethod
    def _dedup_and_sort(items: list[_Candidate]) -> list[_Candidate]:
        # dedup по rel_posix (root/rel), без resolve()
        uniq: dict[str, _Candidate] = {}
        for it in items:
            if it.rel_posix not in uniq:
                uniq[it.rel_posix] = it
        return [uniq[k] for k in sorted(uniq.keys())]

    @staticmethod
    def _to_rel_posix(root: Path, p: Path) -> str | None:
        try:
            return p.relative_to(root).as_posix()
        except Exception:
            return None
