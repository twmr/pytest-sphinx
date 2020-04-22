import textwrap
import doctest
import six

import pytest

from pytest_sphinx import _find_options
from pytest_sphinx import SkippedOutputAssertion


def test_only_options():
    want = textwrap.dedent(
        """
        :options: +NORMALIZE_WHITESPACE
    """
    )

    ret = _find_options(want, "dummy", 10, {})
    assert ret == {4: True}


def test_mulitple_options():
    want = textwrap.dedent(
        """
        :options: +NORMALIZE_WHITESPACE, -ELLIPSIS
    """
    )

    ret = _find_options(want, "dummy", 10, {})
    assert ret == {doctest.NORMALIZE_WHITESPACE: True, doctest.ELLIPSIS: False}


def test_options_and_text():
    want = textwrap.dedent(
        """
        :options: +NORMALIZE_WHITESPACE

        abcedf
        abcedf
    """
    )

    ret = _find_options(want, "dummy", 10, {})
    assert ret == {4: True}


@pytest.mark.parametrize("expr,expected_skip", [("True", True)])
@pytest.mark.parametrize("with_options", [True, False])
def test_skipif_and_text(expr, expected_skip, with_options):
    want = textwrap.dedent(
        """
        :skipif: {}

        abcedf
        abcedf
    """.format(
            expr
        )
    )
    if with_options:
        want = "\n:options: +NORMALIZE_WHITESPACE" + want

    if expected_skip:
        with pytest.raises(SkippedOutputAssertion):
            ret = _find_options(want, "dummy", 10, {"six": six})
    else:
        ret = _find_options(want, "dummy", 10, {"six": six})

        if with_options:
            assert ret == {doctest.NORMALIZE_WHITESPACE: True}
        else:
            assert ret == {}


def test_check_output_with_whitespace_normalization():
    # basically a unittest for a method in the doctest stdlib
    got = "{'a': 3, 'b': 44, 'c': 20}"
    want = textwrap.dedent(
        """
            {'a':    3,
             'b':   44,
             'c':   20}
    """
    )

    assert doctest.OutputChecker().check_output(
        want, got, optionflags=doctest.NORMALIZE_WHITESPACE
    )

    # check_output() with the NORMALIZE_WHITESPACE flag basically does the
    # following
    got = " ".join(got.split())
    want = " ".join(want.split())
    assert got == want


def test_doctest_with_whitespace_normalization(testdir):
    testdir.maketxtfile(
        test_something="""
        .. testcode::

            print("{'a': 3, 'b': 44, 'c': 20}")

        .. testoutput::
            :options: +NORMALIZE_WHITESPACE

            {'a':    3,
             'b':   44,
             'c':   20}
    """
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])
