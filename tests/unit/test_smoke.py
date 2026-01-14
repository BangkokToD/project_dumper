from __future__ import annotations


def test_imports() -> None:
    import domain  # noqa: F401
    from domain.diff import logic  # noqa: F401
    from domain.fs import reader  # noqa: F401
    from domain.fs import rules  # noqa: F401
    from domain.fs import walker  # noqa: F401
    from domain import models  # noqa: F401
    import infrastructure  # noqa: F401
    from infrastructure import filesystem  # noqa: F401
    from infrastructure import gitignore_cache  # noqa: F401
    import project_dumper  # noqa: F401
    from project_dumper import (  # noqa: F401
        config,
        formatter,
        gui,
        walker,
    )
