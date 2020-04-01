import sys
import platform

import _pytest.doctest
import pytest_sphinx


def test_collect_testtextfile(testdir):
    w = testdir.maketxtfile(whatever="")
    checkfile = testdir.maketxtfile(
        test_something="""
        alskdjalsdk
        .. testcode::

            print(2+3)

        .. testoutput::

            5
    """
    )

    for x in (testdir.tmpdir, checkfile):
        items, reprec = testdir.inline_genitems(x)
        assert len(items) == 1
        assert isinstance(items[0], _pytest.doctest.DoctestItem)
        assert isinstance(items[0].parent, pytest_sphinx.SphinxDoctestTextfile)
    # Empty file has no items.
    items, reprec = testdir.inline_genitems(w)
    assert not items


def test_successful_multiline_doctest_in_text_file(testdir):
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

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_successful_doctest_in_text_file(testdir):
    testdir.maketxtfile(
        test_something="""
        alskdjalsdk
        .. testcode::

            print(2+3)

        .. testoutput::

            5
    """
    )

    result = testdir.runpytest("--doctest-modules")
    assert "testcode" not in result.stdout.str()
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_failing_doctest_in_text_file(testdir):
    testdir.maketxtfile(
        test_something="""
        alskdjalsdk
        .. testcode::

            print(2+3)

        .. testoutput::

            9
    """
    )

    result = testdir.runpytest("--doctest-modules")
    assert "FAILURES" in result.stdout.str()
    result.stdout.fnmatch_lines(
        ["002*testcode::*", "004*print(2+3)*", "*=== 1 failed in *"]
    )


def test_expected_exception_doctest(testdir):
    if platform.python_implementation() == "PyPy":
        exception_msg = "integer division by zero"
    elif sys.version_info.major < 3:
        exception_msg = "integer division or modulo by zero"
    else:
        exception_msg = "division by zero"

    testdir.maketxtfile(
        test_something="""
        .. testcode::

            1/0

        .. testoutput::

            Traceback (most recent call last):
              ...
            ZeroDivisionError: {}
    """.format(
            exception_msg
        )
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_global_optionflags(testdir):
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

    result = testdir.inline_run("--doctest-modules")
    result.assertoutcome(passed=1, failed=0)


def test_no_ellipsis_in_global_optionflags(testdir):
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

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(
        ["Expected:", "*ab...gh", "Got:", "*abcdefgh", "*=== 1 failed in *"]
    )
