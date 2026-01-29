import _pytest.doctest
from _pytest.legacypath import Testdir
from _pytest.pytester import Pytester

import pytest_sphinx


def test_collect_testtextfile(pytester: Pytester) -> None:
    empty_txt_file = pytester.maketxtfile(whatever="")
    dot_txt_file = pytester.maketxtfile(
        test_something="""
        alskdjalsdk

        .. testcode::

            print(2+3)

        .. testoutput::

            5
    """
    )

    dot_rst_file = pytester.makefile(
        ".rst",
        test_something="""
        alskdjalsdk

        .. testcode::

            print(2+3)

        .. testoutput::

            5
    """,
    )

    dot_md_file = pytester.makefile(
        ".md",
        test_something="""
        ```{doctest} My example
        >>> 2 + 3
        5
        ```
    """,
    )

    for x in (pytester.path, dot_txt_file, dot_rst_file):
        # run --collect-only in-process
        items, reprec = pytester.inline_genitems(x)

        assert len(items) == 1
        assert isinstance(items[0], _pytest.doctest.DoctestItem)
        assert isinstance(items[0].parent, pytest_sphinx.SphinxDoctestTextfile)

    # Empty file has no items.
    items, reprec = pytester.inline_genitems(empty_txt_file)
    assert not items

    # the md file is not collected even if you explicitly pass the md file to pytest,
    # because it markdown files are not yet supported.
    items, reprec = pytester.inline_genitems(dot_md_file)
    assert not items


def test_successful_multiline_doctest_in_text_file(testdir: Testdir) -> None:
    testdir.maketxtfile(
        test_something="""
        .. testcode::

            print(1+1)
            print(2+3)

        .. testoutput::

            2
            5
    """
    )

    result = testdir.runpytest()
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_successful_doctest_in_text_file(testdir: Testdir) -> None:
    testdir.maketxtfile(
        test_something="""
        alskdjalsdk

        .. testcode::

            print(2+3)

        .. testoutput::

            5
    """
    )

    result = testdir.runpytest()
    assert "testcode" not in result.stdout.str()
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_failing_doctest_in_text_file(testdir: Testdir) -> None:
    testdir.maketxtfile(
        test_something="""
        alskdjalsdk

        .. testcode::

            print(2+3)

        .. testoutput::

            9
    """
    )

    result = testdir.runpytest()
    assert "FAILURES" in result.stdout.str()
    result.stdout.fnmatch_lines(
        ["003*testcode::*", "005*print(2+3)*", "*=== 1 failed in *"]
    )


def test_expected_exception_doctest(testdir: Testdir) -> None:
    testdir.maketxtfile(
        test_something="""
        .. testcode::

            1/0

        .. testoutput::

            Traceback (most recent call last):
              ...
            ZeroDivisionError: division by zero
    """
    )

    result = testdir.runpytest()
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_global_optionflags(testdir: Testdir) -> None:
    testdir.makeini(
        """
        [pytest]
        doctest_optionflags = ELLIPSIS
    """
    )

    testdir.maketxtfile(
        test_something="""
        .. testcode::

            print('abcdefgh')

        .. testoutput::

            ab...gh
    """
    )

    result = testdir.inline_run()
    result.assertoutcome(passed=1, failed=0)


def test_no_ellipsis_in_global_optionflags(testdir: Testdir) -> None:
    testdir.makeini(
        """
        [pytest]
        doctest_optionflags = NORMALIZE_WHITESPACE
    """
    )

    testdir.maketxtfile(
        test_something="""
        .. testcode::

            print('abcdefgh')

        .. testoutput::

            ab...gh
    """
    )

    result = testdir.runpytest()
    result.stdout.fnmatch_lines(
        ["Expected:", "*ab...gh", "Got:", "*abcdefgh", "*=== 1 failed in *"]
    )


def test_skipif_non_builtin(testdir: Testdir) -> None:
    testdir.maketxtfile(
        test_something="""
        .. testcode::

            print('abcdefgh')

        .. testoutput::
            :skipif: pd is not None

            NOT EVALUATED
    """
    )

    result = testdir.runpytest()
    result.stdout.fnmatch_lines(["*NameError:*name 'pd' is not defined"])


def test_doctest_namespace(testdir: Testdir) -> None:
    testdir.maketxtfile(
        test_something="""
        .. testcode::

           sys.version_info is not None
    """
    )

    testdir.makeconftest(
        """
        import sys

        import pytest

        @pytest.fixture(autouse=True)
        def add_sys(doctest_namespace):
            doctest_namespace["sys"] = sys
        """
    )

    result = testdir.runpytest()
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_doctest_directive(testdir: Testdir) -> None:
    testdir.maketxtfile(
        test_something=r"""
        This is a paragraph. This is the
        next sentence.

        .. doctest::

           >>> assert False
           Traceback (most recent call last):
           ...
           AssertionError
    """
    )

    result = testdir.runpytest()
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])

    testdir.maketxtfile(
        test_something=r"""
        This is a paragraph. This is the
        next sentence.

        .. doctest::

           >>> assert False
    """
    )

    result = testdir.runpytest()
    result.stdout.fnmatch_lines(["*=== 1 failed in *"])
