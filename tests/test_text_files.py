import _pytest.doctest
import pytest_sphinx


def test_collect_testtextfile(testdir):
    w = testdir.maketxtfile(whatever="")
    checkfile = testdir.maketxtfile(test_something="""
        alskdjalsdk
        .. testcode::

            print(2+3)

        .. testoutput::

            5
    """)

    for x in (testdir.tmpdir, checkfile):
        items, reprec = testdir.inline_genitems(x)
        assert len(items) == 1
        assert isinstance(items[0],
                          _pytest.doctest.DoctestItem)
        assert isinstance(items[0].parent,
                          pytest_sphinx.SphinxDoctestTextfile)
    # Empty file has no items.
    items, reprec = testdir.inline_genitems(w)
    assert not items


def test_successful_doctest_in_text_file(testdir):
    testdir.maketxtfile(test_something="""
        alskdjalsdk
        .. testcode::

            print(2+3)

        .. testoutput::

            5
    """)

    result = testdir.runpytest('--doctest-modules')
    assert 'testcode' not in result.stdout.str()
    result.stdout.fnmatch_lines([
        '*=== 1 passed in *'])


def test_failing_doctest_in_text_file(testdir):
    testdir.maketxtfile(test_something="""
        alskdjalsdk
        .. testcode::

            print(2+3)

        .. testoutput::

            9
    """)

    result = testdir.runpytest('--doctest-modules')
    assert 'FAILURES' in result.stdout.str()
    result.stdout.fnmatch_lines([
        '002*testcode::*',
        '004*print(2+3)*',
        '*=== 1 failed in *'])