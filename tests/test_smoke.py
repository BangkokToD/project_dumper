from __future__ import annotations


def test_imports() -> None:
    import project_dumper  # noqa: F401
    from project_dumper import (  # noqa: F401
        config,
        formatter,
        gitignore_cache,
        gui,
        reader,
        walker,
    )
