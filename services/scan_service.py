from __future__ import annotations

from pathlib import Path

from domain.fs.reader import read_text_streaming
from domain.fs.walker import Walker
from domain.models import DumpFile, ScanMode, ScanOptions, ScanResult
from config.model import Config


class ScanService:
    """
    Use-case сервис сканирования проекта.

    Цель: собрать ScanResult без привязки к Qt, чтобы было тестируемо.
    """

    @staticmethod
    def scan(root: Path, cfg: Config, options: ScanOptions) -> ScanResult:
        """
        Просканировать проект и вернуть результат.

        Актуальные правила:
        - В дереве collapsed dirs видны, но их содержимое заменяется на "…".
        - В дампе (файлы) элементы под collapsed dirs и вручную скрытые файлы
          НЕ показываются по умолчанию и появляются только в режиме ignore_collapsed.
        - Режимы:
            * TREE_AND_FILES: дерево + файлы
            * ONLY_FILES: только файлы (tree=None)
            * ONLY_TREE: только дерево (files=[])

        Args:
            root: Корневая директория проекта.
            cfg: Текущий конфиг (временно используем напрямую).
            options: Опции сканирования (collapsed/excluded/...).

        Returns:
            ScanResult(tree, files).
        """
        w = Walker()
        w.cfg = cfg
        w.git.build(root)

        tree: str | None = None
        if options.mode != ScanMode.ONLY_FILES:
            tree = w.build_tree(root, options)

        out_files: list[DumpFile] = []

        if options.mode != ScanMode.ONLY_TREE:
            files_paths = w.iter_files(root)

            collapsed_dirs = set(options.collapsed_dirs)
            if options.ignore_collapsed:
                collapsed_dirs = set()

            for p in files_paths:
                # В режиме "игнорировать" показываем файлы, скрытые вручную (excluded_files)
                if (not options.ignore_manual_excluded) and (p in options.excluded_files):
                    continue

                # По умолчанию скрытое через collapsed не показываем в дампе (файлах)
                hide = _is_under_any(p, collapsed_dirs)
                if hide:
                    continue

                rel = p.relative_to(root).as_posix()

                content = "".join(read_text_streaming(p, cfg))
                out_files.append(DumpFile(path=rel, content=content, skipped_reason=None))

        return ScanResult(tree=tree, files=out_files)


def _is_under_any(p: Path, roots: set[Path]) -> bool:
    """
    Проверить, находится ли путь p внутри любой директории из roots.
    """
    if not roots:
        return False
    for d in roots:
        try:
            if p.is_relative_to(d):
                return True
        except Exception:
            # fallback на строковое сравнение
            if str(p).startswith(str(d)):
                return True
    return False
