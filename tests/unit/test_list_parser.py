import pytest

from domain.list_scan.parser import parse_list_tokens


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # 1
        ("нужно проверить config/model.py и domain/* срочно", ["config/model.py", "domain/*"]),
        # 2
        ("\"config/model.py\", (domain/*); pyproject.toml.", ["config/model.py", "domain/*", "pyproject.toml"]),
        # 3
        ("ls src/ && cat README.md", ["src", "README.md"]),
        # 4
        ("./build.sh ../dist/output.tar.gz", []),
        # 5
        (r"config\model.py", []),
        # 6
        ("a//b.py", []),
        # 7
        ("/etc/passwd", []),
        # 8
        ("report/./final.txt", []),
        # 9
        ("версия v1.2.3 релиз release-0.3.0", []),
    ],
)
def test_parse_list_tokens_cases_11_1(text: str, expected: list[str]) -> None:
    assert parse_list_tokens(text) == expected
