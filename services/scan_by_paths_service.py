from __future__ import annotations
import os
from dataclasses import dataclass, replace

from pathlib import Path
from typing import Iterable, Protocol


from config.model import Config
from domain.fs.reader import read_text_streaming
from domain.fs import rules
from infrastructure.gitignore_cache import GitignoreCache
from domain.list_scan.models import SelectedPath, resolve_selected_paths
from domain.models import DumpFile, ScanResult

class _ListScanSettingsLike(Protocol):
    star_is_recursive: bool
    ignore_filters: bool
    expand_dir_match: bool




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

    Commit 7 (семантика list_scan):
    - star_is_recursive: считать '*' рекурсивной (как '**/*'), не ломая уже существующие '**'
    - dir-токены: файлы первого уровня; если файлов нет — рекурсивно (правило 7.3.1-аналог)
    - expand_dir_match: если паттерн матчится в директорию — добавить файлы (1-й уровень или рекурсивно по правилам)

    Commit 8 (фильтры list_scan):
    - применение domain.fs.rules + GitignoreCache (если ignore_filters=false)
    - ignore_filters=true отключает ignore_hidden/ignore_dirs/ignore_files/.gitignore
    - security-policy: include_env=false всегда скрывает .env (даже при ignore_filters=true)
    """

    @staticmethod
    def scan(
        root: Path,
        tokens: list[str],
        cfg: Config,
        list_scan_settings: _ListScanSettingsLike,
    ) -> ScanResult:
        selected = resolve_selected_paths(root, tokens, follow_symlinks=cfg.follow_symlinks)
        selected = ScanByPathsService._apply_env_security(selected, cfg)

        git = GitignoreCache()
        if not list_scan_settings.ignore_filters:
            git.build(root)


        # Минимальный fail-fast (только bad pattern syntax из Commit 5).
        bad = [s.raw for s in selected if s.kind == "pattern" and s.bad_pattern_syntax]
        if bad:
            raise ValueError("Bad pattern syntax: " + ", ".join(bad))

        candidates = ScanByPathsService._collect_candidates(
            root,
            selected,
            cfg=cfg,
            git=git,
            list_scan_settings=list_scan_settings,
            follow_symlinks=cfg.follow_symlinks,
        )

        ordered = ScanByPathsService._dedup_and_sort(candidates)

        out_files: list[DumpFile] = []
        for c in ordered:
            content = "".join(read_text_streaming(c.abs_path, cfg))
            out_files.append(DumpFile(path=c.rel_posix, content=content, skipped_reason=None))

        return ScanResult(tree=None, files=out_files)

    @staticmethod
    def _apply_env_security(selected: list[SelectedPath], cfg: Config) -> list[SelectedPath]:
        # include_env=false: явный запрос .env трактуем как missing (скрыт настройками).
        if cfg.include_env:
            return selected
        out: list[SelectedPath] = []
        for s in selected:
            if s.kind == "file" and s.resolved.name == ".env":
                out.append(replace(s, kind="missing", missing_reason="скрыт настройками"))
            else:
                out.append(s)
        return out

    @staticmethod
    def _should_enter_dir(path: Path, *, cfg: Config, git: GitignoreCache, ignore_filters: bool) -> bool:
        if ignore_filters:
            return True
        return not rules.is_ignored_dir(path, cfg, git)

    @staticmethod
    def _should_include_file(
        root: Path,
        path: Path,
        *,
        cfg: Config,
        git: GitignoreCache,
        ignore_filters: bool,
    ) -> bool:
        # security-policy: .env не показываем никогда, если include_env=false
        if path.name == ".env" and not cfg.include_env:
            return False

        if ignore_filters:
            return True

        if ScanByPathsService._is_under_ignored_dir(root, path, cfg=cfg, git=git):
            return False
        return not rules.is_ignored_file(path, cfg, git)

    @staticmethod
    def _is_under_ignored_dir(root: Path, p: Path, *, cfg: Config, git: GitignoreCache) -> bool:
        cur = p.parent
        while True:
            if cur == root:
                return False
            if rules.is_ignored_dir(cur, cfg, git):
                return True
            nxt = cur.parent
            if nxt == cur:
                return False
            cur = nxt

    @staticmethod
    def _collect_candidates(
        root: Path,
        selected: Iterable[SelectedPath],
        *,
        cfg: Config,
        git: GitignoreCache,
        list_scan_settings: _ListScanSettingsLike,
        follow_symlinks: bool,
    ) -> list[_Candidate]:

        out: list[_Candidate] = []

        for s in selected:
            if s.kind == "file":
                if not ScanByPathsService._is_allowed_path(root, s.resolved, follow_symlinks=follow_symlinks):
                    continue
                if not ScanByPathsService._should_include_file(
                    root,
                    s.resolved,
                    cfg=cfg,
                    git=git,
                    ignore_filters=list_scan_settings.ignore_filters,
                ):
                    continue
                rel = ScanByPathsService._to_rel_posix(root, s.resolved)
                if rel is not None:
                    out.append(_Candidate(abs_path=s.resolved, rel_posix=rel))
                continue

            if s.kind == "dir":
                # Явная директория без wildcard:
                # - включаем файлы первого уровня;
                # - если файлов первого уровня нет -> рекурсивно (7.3.1-аналог: иначе "дампить нечего").
                if not ScanByPathsService._is_allowed_path(root, s.resolved, follow_symlinks=follow_symlinks):
                    continue
                if not ScanByPathsService._should_enter_dir(
                    s.resolved,
                    cfg=cfg,
                    git=git,
                    ignore_filters=list_scan_settings.ignore_filters,
                ):
                    continue
                first = list(
                    ScanByPathsService._iter_dir_files_first_level(
                        root,
                        s.resolved,
                        cfg=cfg,
                        git=git,
                        ignore_filters=list_scan_settings.ignore_filters,
                        follow_symlinks=follow_symlinks,
                    )
                )

                if first:
                    for ch in first:
                        rel = ScanByPathsService._to_rel_posix(root, ch)
                        if rel is not None:
                            out.append(_Candidate(abs_path=ch, rel_posix=rel))
                else:
                    for ch in ScanByPathsService._iter_dir_files_recursive(
                        root,
                        s.resolved,
                        cfg=cfg,
                        git=git,
                        ignore_filters=list_scan_settings.ignore_filters,
                        follow_symlinks=follow_symlinks,
                    ):

                        rel = ScanByPathsService._to_rel_posix(root, ch)
                        if rel is not None:
                            out.append(_Candidate(abs_path=ch, rel_posix=rel))

                continue

            if s.kind == "pattern":
                # Path.glob для паттернов относительно root.
                pattern = ScanByPathsService._apply_star_is_recursive(s.raw, enabled=list_scan_settings.star_is_recursive)
                is_recursive_pattern = ("**" in pattern)

                try:
                    for m in root.glob(pattern):
                        if not ScanByPathsService._is_allowed_path(root, m, follow_symlinks=follow_symlinks):
                            continue

                        if m.is_file():
                            if not ScanByPathsService._should_include_file(
                                root,
                                m,
                                cfg=cfg,
                                git=git,
                                ignore_filters=list_scan_settings.ignore_filters,
                            ):
                                continue

                            rel = ScanByPathsService._to_rel_posix(root, m)
                            if rel is not None:
                                out.append(_Candidate(abs_path=m, rel_posix=rel))
                            continue

                        # директории сами по себе не элементы результата
                        if not m.is_dir():
                            continue

                        if not ScanByPathsService._should_enter_dir(
                            m,
                            cfg=cfg,
                            git=git,
                            ignore_filters=list_scan_settings.ignore_filters,
                        ):
                            continue

                        # если паттерн уже рекурсивный (**), файлы и так будут матчиться напрямую;
                        # не разворачиваем директории дополнительно, чтобы не плодить дубликаты.
                        if is_recursive_pattern:
                            continue

                        if not list_scan_settings.expand_dir_match:
                            continue

                        # expand_dir_match:
                        # - если star_is_recursive включён -> рекурсивно
                        # - иначе -> файлы первого уровня; если их нет -> рекурсивно (7.3.1)
                        if list_scan_settings.star_is_recursive:
                            for ch in ScanByPathsService._iter_dir_files_recursive(
                                root,
                                m,
                                cfg=cfg,
                                git=git,
                                ignore_filters=list_scan_settings.ignore_filters,
                                follow_symlinks=follow_symlinks,
                            ):

                                rel = ScanByPathsService._to_rel_posix(root, ch)
                                if rel is not None:
                                    out.append(_Candidate(abs_path=ch, rel_posix=rel))
                        else:
                            first = list(
                                ScanByPathsService._iter_dir_files_first_level(
                                    root,
                                    m,
                                    cfg=cfg,
                                    git=git,
                                    ignore_filters=list_scan_settings.ignore_filters,
                                    follow_symlinks=follow_symlinks,
                                )
                            )

                            if first:
                                for ch in first:
                                    rel = ScanByPathsService._to_rel_posix(root, ch)
                                    if rel is not None:
                                        out.append(_Candidate(abs_path=ch, rel_posix=rel))
                            else:
                                for ch in ScanByPathsService._iter_dir_files_recursive(
                                    root,
                                    m,
                                    cfg=cfg,
                                    git=git,
                                    ignore_filters=list_scan_settings.ignore_filters,
                                    follow_symlinks=follow_symlinks,
                                ):

                                    rel = ScanByPathsService._to_rel_posix(root, ch)
                                    if rel is not None:
                                        out.append(_Candidate(abs_path=ch, rel_posix=rel))

                except Exception:
                    # Детальная диагностика будет отдельным коммитом.
                    pass
                continue

            # missing — в этом коммите просто игнорируем (fail-fast и причины — позже).

        return out

    @staticmethod
    def _apply_star_is_recursive(pattern: str, *, enabled: bool) -> str:
        """
        star_is_recursive (см. ТЗ: считать '*' рекурсивной как '**/*'):
        - если в паттерне уже есть компонент '**' — не трогаем (чтобы не "ломать **")
        - иначе делаем компонентную трансформацию:
            * '*' (отдельный компонент) -> '**/*'
            * '*.py' / 'a*b' (звёздочка внутри компонента) -> добавляем '**/' перед компонентом
              Примеры:
                '*.py' -> '**/*.py'
                'domain/*.py' -> 'domain/**/*.py'
                'match_dir/*' -> 'match_dir/**/*'

        """
        if not enabled:
            return pattern
        # нормализуем ввод (на всякий случай)
        pat = pattern.replace("\\", "/")

        parts = pat.split("/")
        # если пользователь уже явно задал рекурсию через '**' — не модифицируем
        if any(p == "**" for p in parts):
            return pat

        out_parts: list[str] = []
        for p in parts:
            if p == "":
                # сохраняем ведущие/хвостовые слэши как есть
                out_parts.append(p)
                continue

            if "*" not in p:
                out_parts.append(p)
                continue

            if p == "*":
                # '*' как компонент становится '**/*'
                if not out_parts or out_parts[-1] != "**":
                    out_parts.append("**")
                out_parts.append("*")
                continue

            # '*' внутри компонента (например '*.py'): делаем '**/<component>'
            if not out_parts or out_parts[-1] != "**":
                out_parts.append("**")
            out_parts.append(p)

        return "/".join(out_parts)



    @staticmethod
    def _iter_dir_files_first_level(
        root: Path,
        dir_path: Path,
        *,
        cfg: Config,
        git: GitignoreCache,
        ignore_filters: bool,
        follow_symlinks: bool,
    ) -> Iterable[Path]:

        try:
            for ch in dir_path.iterdir():
                if not ch.is_file():
                    continue
                if not ScanByPathsService._is_allowed_path(root, ch, follow_symlinks=follow_symlinks):
                    continue
                if not ScanByPathsService._should_include_file(
                    root,
                    ch,
                    cfg=cfg,
                    git=git,
                    ignore_filters=ignore_filters,
                ):

                    continue
                yield ch
        except Exception:
            return

    @staticmethod
    def _iter_dir_files_recursive(
        root: Path,
        dir_path: Path,
        *,
        cfg: Config,
        git: GitignoreCache,
        ignore_filters: bool,
        follow_symlinks: bool,
    ) -> Iterable[Path]:
        """
        Рекурсивный сбор файлов без добавления директорий как элементов результата.
        Используем os.walk, чтобы уважать follow_symlinks (followlinks).
        При ignore_filters=False также не заходим в игнорируемые директории (как Walker).
        """

        """
        Рекурсивный сбор файлов без добавления директорий как элементов результата.
        Используем os.walk, чтобы уважать follow_symlinks (followlinks).
        """
        try:
            for base, dirs, files in os.walk(dir_path, followlinks=follow_symlinks):
                base_p = Path(base)

                if not ignore_filters:
                    kept: list[str] = []
                    for d in list(dirs):
                        dp = base_p / d
                        if not ScanByPathsService._is_allowed_path(root, dp, follow_symlinks=follow_symlinks):
                            continue
                        if rules.is_ignored_dir(dp, cfg, git):
                            continue
                        kept.append(d)
                    dirs[:] = kept


                for name in files:
                    p = base_p / name
                    if not ScanByPathsService._is_allowed_path(root, p, follow_symlinks=follow_symlinks):
                        continue
                    if not ScanByPathsService._should_include_file(
                        root,
                        p,
                        cfg=cfg,
                        git=git,
                        ignore_filters=ignore_filters,
                    ):

                        continue
                    yield p
        except Exception:
            return

    @staticmethod
    def _is_allowed_path(root: Path, p: Path, *, follow_symlinks: bool) -> bool:
        """
        Минимально применяем follow_symlinks к результатам glob:
        - если follow_symlinks=False, отбрасываем файлы/диры-симлинки,
          а также любые пути, находящиеся под симлинк-директорией.
        """
        if follow_symlinks:
            return True

        try:
            if p.is_symlink():
                return False
            rel = p.relative_to(root)
        except Exception:
            return False

        cur = root
        # проверяем только директории-предки
        for part in rel.parts[:-1]:
            cur = cur / part
            try:
                if cur.is_symlink():
                    return False
            except Exception:
                return False
        return True



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
