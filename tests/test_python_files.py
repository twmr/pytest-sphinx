import textwrap

from _pytest.legacypath import Testdir


def test_syntax_error_in_module_doctest(testdir: Testdir) -> None:

    testdir.makepyfile(
        textwrap.dedent(
            """
        '''
        .. doctest::

            >>> 3+
        '''
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(
        ["UNEXPECTED EXCEPTION: SyntaxError('invalid syntax',*"]
    )


def test_failing_module_doctest(testdir: Testdir) -> None:

    testdir.makepyfile(
        textwrap.dedent(
            """
        '''
        .. doctest::

            >>> print(2+5)
            3
        '''
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    assert "FAILURES" in result.stdout.str()
    print(f"result.stdout: {result.stdout}")
    result.stdout.fnmatch_lines(
        ["002*doctest::*", "004*print(2+5)*", "*=== 1 failed in *"]
    )


def test_failing_function_doctest(testdir: Testdir) -> None:
    testdir.makepyfile(
        textwrap.dedent(
            """
        # simple comment
        GLOBAL_VAR = True

        def func():
            '''
            .. doctest::

               >>> print(2+5)
               3
            '''
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    assert "FAILURES" in result.stdout.str()
    assert "GLOBAL_VAR" not in result.stdout.str()
    result.stdout.fnmatch_lines(
        ["006*doctest::*", "008*print(2+5)*", "*=== 1 failed in *"]
    )


def test_working_module_doctest(testdir: Testdir) -> None:

    testdir.makepyfile(
        textwrap.dedent(
            """
        '''
        .. doctest::

           >>> print(2+5)
           7
        '''
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_working_function_doctest(testdir: Testdir) -> None:
    testdir.makepyfile(
        textwrap.dedent(
            """
        # simple comment
        GLOBAL_VAR = True

        def func():
            '''
            .. docutils::

               >>> print(2+5)
               7
            '''
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_working_module_doctest_nospaces(testdir: Testdir) -> None:

    testdir.makepyfile(
        textwrap.dedent(
            """
        '''
        .. docutils::
            >>>print(2+5)
            7
        '''
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["* lacks blank after *"])
    result.stdout.fnmatch_lines(["*=== 1 error in *"])


def test_multiple_doctests_in_single_file(testdir: Testdir) -> None:

    testdir.makepyfile(
        textwrap.dedent(
            """
        def foo():
            \"\"\"
            .. docutils::

                >>> print('1adlfadsf')
                1...
            \"\"\"
            pass

        def bar():
            \"\"\"
            .. docutils::

                >>> print('1adlfadsf')
                1...
            \"\"\"
            pass
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["*=== 2 passed in *"])


def test_indented(testdir: Testdir) -> None:
    testdir.makepyfile(
        textwrap.dedent(
            """
    '''
    Examples:
        some text

        .. docutils::

            >>> print("Banana")
            Banana
    '''
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_workaround_for_doctest_mockobj_bug(testdir: Testdir) -> None:
    # see https://github.com/pytest-dev/pytest/issues/3456

    testdir.makepyfile(
        textwrap.dedent(
            """
        \"\"\"
        .. docutils::

            >>> print("Banana")
            Banana

        \"\"\"

        from unittest.mock import call
    """
        )
    )

    result = testdir.runpytest("--doctest-modules")
    result.stdout.fnmatch_lines(["*=== 1 passed in *"])


def test_with_conftest(testdir: Testdir) -> None:
    content = """
        \"\"\"

        .. doctest::

           >>> print('abc')
           abc

        \"\"\"
    """

    testdir.maketxtfile(test_something=content)

    testdir.makeconftest(content)

    # what do we expect?
    result = testdir.runpytest("--doctest-modules")
    # 2 test passed one test in conftest.py and one in something.py
    result.stdout.fnmatch_lines(["*=== 2 passed in *"])
