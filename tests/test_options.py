import textwrap
import doctest
import six

import pytest

from pytest_sphinx import _extract_options


def test_only_options():
    section_content = textwrap.dedent(
        """
        :options: +NORMALIZE_WHITESPACE
    """
    )

    import pdb; pdb.set_trace()
    content, options = _extract_options(section_content)
    assert options.flags == {4: True}
    assert content == ''


def test_mulitple_options():
    want = textwrap.dedent(
        """
        :options: +NORMALIZE_WHITESPACE, -ELLIPSIS
    """
    )

    content, options = _extract_options(want)
    assert options.flags == {doctest.NORMALIZE_WHITESPACE: True, doctest.ELLIPSIS: False}


def test_options_and_text():
    section_content = textwrap.dedent(
        """
        :options: +NORMALIZE_WHITESPACE

        abcedf
        abcedf
    """
    )

    content, options = _extract_options(section_content)
    assert options.flags == {4: True}
    assert content == "abcedf\nabcedf"


# @pytest.mark.parametrize("expr,expected_skip", [("True", True)])
# @pytest.mark.parametrize("with_options", [True, False])
# def test_skipif_and_text(expr, expected_skip, with_options):
#     want = textwrap.dedent(
#         """
#         :skipif: {}

#         abcedf
#         abcedf
#     """.format(
#             expr
#         )
#     )
#     if with_options:
#         want = "\n:options: +NORMALIZE_WHITESPACE\n" + want

#     if expected_skip:
#         with pytest.raises(SkippedOutputAssertion):
#             ret = _extract_options(want)(want, "dummy", 10, {"six": six})
#     else:
#         ret = _find_options(want, "dummy", 10, {"six": six})

#         if with_options:
#             assert ret == {doctest.NORMALIZE_WHITESPACE: True}
#         else:
#             assert ret == {}


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


def test_parse_options():
    section_content = textwrap.dedent(
        """
    :options: +NORMALIZE_WHITESPACE

    {'a':    3,
     'b':   44,
     'c':   20}
    """
    )

    remaining_content, options = _extract_options(section_content)
    assert remaining_content == "\n".join(
        ("{'a':    3,", " 'b':   44,", " 'c':   20}")
    )

    assert options.flags == {4: True}
    assert options.skipif_expr is None
    assert options.hide is False


def test_parse_options_all_opts():
    section_content = textwrap.dedent(
        """
    :hide:
    :options: +NORMALIZE_WHITESPACE
    :skipif: True

    {'a':    3,
     'b':   44,
     'c':   20}
    """
    )

    remaining_content, options = _extract_options(section_content)
    assert remaining_content == "\n".join(
        ("{'a':    3,", " 'b':   44,", " 'c':   20}")
    )

    assert options.flags == {4: True}
    assert options.skipif_expr == 'True'
    assert options.hide is True
