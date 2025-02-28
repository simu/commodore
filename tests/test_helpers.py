"""
Unit-tests for helpers
"""
from pathlib import Path
from typing import Callable
import textwrap
import pytest

import commodore.helpers as helpers
from commodore.config import Config
from commodore.component import Component, component_dir


def test_apierror():
    e = helpers.ApiError("test")
    assert f"{e}" == "test"

    try:
        raise helpers.ApiError("test2")
    except helpers.ApiError as e2:
        assert f"{e2}" == "test2"


def test_clean_working_tree(tmp_path: Path):
    cfg = Config(work_dir=tmp_path)
    cfg.inventory.ensure_dirs()
    d = component_dir(tmp_path, "test")
    assert not d.is_dir()
    Component("test", work_dir=tmp_path)
    assert d.is_dir()
    helpers.clean_working_tree(cfg)
    assert d.is_dir()


def _test_yaml_dump_fun(
    dumpfunc: Callable[[str, Path], None], tmp_path: Path, input, expected
):
    output = tmp_path / "test.yaml"
    dumpfunc(input, output)
    with open(output) as f:
        data = "".join(f.readlines())
    assert expected == data


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            {"a": 1, "b": "test"},
            textwrap.dedent(
                """
                a: 1
                b: test
                """
            )[1:],
        ),
        (
            {"a": [1, 2], "b": "test"},
            textwrap.dedent(
                """
                a:
                - 1
                - 2
                b: test
                """
            )[1:],
        ),
        (
            {"a": {"test": 1}, "b": "test"},
            textwrap.dedent(
                """
                a:
                  test: 1
                b: test
                """
            )[1:],
        ),
        (
            {"a": "first line\nsecond line", "b": "test"},
            textwrap.dedent(
                """
                a: |-
                  first line
                  second line
                b: test
                """
            )[1:],
        ),
    ],
)
def test_yaml_dump(tmp_path: Path, input, expected):
    _test_yaml_dump_fun(helpers.yaml_dump, tmp_path, input, expected)


@pytest.mark.parametrize(
    "input,expected",
    [
        (
            [{"a": 1}, {"b": "test"}],
            textwrap.dedent(
                """
                    a: 1
                    ---
                    b: test
                    """
            )[1:],
        ),
        (
            [{"a": {"test": "first line\nsecond line"}}, {"b": "test"}],
            textwrap.dedent(
                """
                a:
                  test: |-
                    first line
                    second line
                ---
                b: test
                """
            )[1:],
        ),
        (
            [{"a": [1, 2]}, {"b": "test"}],
            textwrap.dedent(
                """
                a:
                - 1
                - 2
                ---
                b: test
                """
            )[1:],
        ),
    ],
)
def test_yaml_dump_all(tmp_path: Path, input, expected):
    _test_yaml_dump_fun(helpers.yaml_dump_all, tmp_path, input, expected)
