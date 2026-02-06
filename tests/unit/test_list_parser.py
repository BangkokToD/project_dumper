import pytest

from domain.list_scan.parser import parse_list_tokens


def test_case_1_two_tokens():
    # 11.1(1)
    text = "нужно проверить config/model.py и domain/* срочно"
    assert parse_list_tokens(text) == ["config/model.py", "domain/*"]


def test_case_2_trim_quotes_parens_commas_semicolons_and_taildot():
    # 11.1(2)
    text = '"config/model.py", (domain/*); pyproject.toml.'
    assert parse_list_tokens(text) == ["config/model.py", "domain/*", "pyproject.toml"]


def test_case_3_no_path_like_token():
    # 11.1(3)
    text = "README"
    assert parse_list_tokens(text) == []


def test_case_4_forbidden_forms_dotdot_and_relative_prefixes():
    # 11.1(4)
    text = "./config/a.py ../b.py a/../c.py"
    assert parse_list_tokens(text) == []


def test_case_5_backslash_rule_drops_neighbor_candidates():
    # 11.1(5)
    text = r"config\model.py"
    assert parse_list_tokens(text) == []


def test_case_6_double_slash_is_forbidden():
    # 11.1(6)
    text = "a//b.py"
    assert parse_list_tokens(text) == []


def test_case_7_dot_segment_is_forbidden():
    # 11.1(7)
    text = "a/./b.py"
    assert parse_list_tokens(text) == []


def test_case_8_double_dot_inside_segment_is_ok():
    # 11.1(8)
    text = "a..b.py"
    assert parse_list_tokens(text) == ["a..b.py"]


def test_case_9_tail_slash_removed():
    # 11.1(9)
    text = "domain/"
    assert parse_list_tokens(text) == ["domain"]
