from __future__ import annotations

from pathlib import Path

from config.model import Config
from domain.fs.reader import read_text_file
from domain.fs.walker import Walker
from domain.term_replace.matcher import (
    find_term_occurrences,
    group_occurrences_by_variant,
)
from domain.term_replace.models import TermOccurrence, TermVariant


class TermReplaceService:
    """Сервис сканирования проекта для вкладки «Замена».

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
        if not root.exists() or not root.is_dir():
            return []

        walker = Walker()
        walker.cfg = cfg
        walker.git.build(root)

        occurrences: list[TermOccurrence] = []

        for path in walker.iter_files(root):
            read_result = read_text_file(path, cfg)
            if read_result.content is None:
                continue

            relative_path = path.relative_to(root).as_posix()
            occurrences.extend(
                find_term_occurrences(
                    read_result.content,
                    source_term,
                    relative_path,
                )
            )

        return group_occurrences_by_variant(occurrences)