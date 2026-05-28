from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

from config.model import Config
from domain.fs.reader import read_text_file
from domain.fs.walker import Walker
from domain.term_replace.applier import apply_preview_changes_to_text
from domain.term_replace.matcher import (
    find_term_occurrences,
    group_occurrences_by_variant,
)
from domain.term_replace.models import (
    ReplacementApplyReport,
    ReplacementPreview,
    ReplacementRule,
    TermOccurrence,
    TermVariant,
)
from domain.term_replace.preview import build_replacement_preview as build_domain_replacement_preview


class TermReplaceService:
    """Сервис операций вкладки «Замена».

    Сервис находится между UI и domain layer:
    - использует существующий Walker для обхода проекта;
    - использует существующий read_text_file для чтения текстовых файлов;
    - делегирует поиск и группировку чистому доменному matcher.
    """

    @staticmethod
    def scan(root: Path, source_term: str, cfg: Config) -> list[TermVariant]:
        """Просканировать проект и вернуть найденные формы термина.

        Args:
            root: Корневая директория проекта.
            source_term: Базовый термин для поиска русских словоформ.
            cfg: Текущая конфигурация Project Dumper.

        Returns:
            Список найденных форм, сгруппированных по точному написанию.
        """
        occurrences: list[TermOccurrence] = []

        for relative_path, content in TermReplaceService._read_project_text_files(root, cfg).items():
            occurrences.extend(
                find_term_occurrences(
                    content,
                    source_term,
                    relative_path,
                )
            )

        return group_occurrences_by_variant(occurrences)

    @staticmethod
    def build_preview(
        root: Path,
        rules: Iterable[ReplacementRule],
        cfg: Config,
    ) -> ReplacementPreview:
        """Построить preview замен по файлам проекта.

        Args:
            root: Корневая директория проекта.
            rules: Правила замен по точным найденным формам.
            cfg: Текущая конфигурация Project Dumper.

        Returns:
            Preview изменений, сгруппированный по файлам.
        """
        files = TermReplaceService._read_project_text_files(root, cfg)
        return build_domain_replacement_preview(files, rules)

    @staticmethod
    def apply_preview(root: Path, preview: ReplacementPreview) -> ReplacementApplyReport:
        """Применить отмеченные изменения preview к реальным файлам.

        Перед записью каждого файла сервис перечитывает текущее содержимое и
        сравнивает hash с hash, сохранённым при построении preview. Если файл
        изменился, он не записывается и попадает в список конфликтов.

        Args:
            root: Корневая директория проекта.
            preview: Preview изменений для применения.

        Returns:
            Отчёт о применении замен.
        """
        changed_files = 0
        applied_changes = 0
        skipped_changes = 0
        conflicted_files: list[str] = []

        for preview_file in preview.files:
            changes = list(preview_file.changes)
            if not changes:
                continue

            enabled_changes = [change for change in changes if change.enabled]
            if not enabled_changes:
                skipped_changes += len(changes)
                continue

            file_path = TermReplaceService._resolve_preview_file_path(
                root,
                preview_file.file_path,
            )
            current_content = (
                file_path.read_text(encoding="utf-8")
                if file_path is not None and file_path.exists() and file_path.is_file()
                else None
            )

            if (
                current_content is None
                or _content_hash(current_content) != preview_file.content_hash
            ):
                conflicted_files.append(preview_file.file_path)
                skipped_changes += len(changes)
                continue

            updated_content = apply_preview_changes_to_text(
                current_content,
                enabled_changes,
            )

            if updated_content != current_content:
                file_path.write_text(updated_content, encoding="utf-8")
                changed_files += 1

            applied_changes += len(enabled_changes)
            skipped_changes += len(changes) - len(enabled_changes)

        return ReplacementApplyReport(
            changed_files=changed_files,
            applied_changes=applied_changes,
            skipped_changes=skipped_changes,
            conflicted_files=conflicted_files,
        )

    @staticmethod
    def _read_project_text_files(root: Path, cfg: Config) -> dict[str, str]:
        """Прочитать текстовые файлы проекта с учётом правил Project Dumper.

        Args:
            root: Корневая директория проекта.
            cfg: Текущая конфигурация Project Dumper.

        Returns:
            Словарь ``относительный POSIX-путь -> содержимое файла``.
        """
        if not root.exists() or not root.is_dir():
            return {}

        walker = Walker()
        walker.cfg = cfg
        walker.git.build(root)

        files: dict[str, str] = {}

        for path in walker.iter_files(root):
            read_result = read_text_file(path, cfg)
            if read_result.content is None:
                continue

            relative_path = path.relative_to(root).as_posix()
            files[relative_path] = read_result.content

        return files

    @staticmethod
    def _resolve_preview_file_path(root: Path, file_path: str) -> Path | None:
        """Безопасно получить путь файла preview внутри корня проекта.

        Args:
            root: Корневая директория проекта.
            file_path: Относительный POSIX-путь из preview.

        Returns:
            Абсолютный путь файла или ``None``, если путь выходит за root.
        """
        try:
            root_resolved = root.resolve()
            target = (root / file_path).resolve()
            target.relative_to(root_resolved)
            return target
        except (OSError, ValueError):
            return None


def _content_hash(content: str) -> str:
    """Посчитать hash содержимого файла для проверки устаревания preview.

    Args:
        content: Исходное содержимое файла.

    Returns:
        SHA-256 hash в hex-формате.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
