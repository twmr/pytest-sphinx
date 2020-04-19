""" Run tests that call "sphinx-build -M doctest". """
import subprocess
import sys
import textwrap

import pytest


pytestmark = pytest.mark.skipif(
    sys.version_info.major == 2, reason="problems with shinx in py2"
)


class SphinxDoctestRunner:
    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        subprocess.check_output(
            [
                "sphinx-quickstart",
                "-v",
                "0.1",
                "-r",
                "0.1",
                "-l",
                "en",
                "-a",
                "my.name",
                "--ext-doctest",  # enable doctest extension
                "--sep",
                "-p",
                "demo",
                ".",
            ]
        )

    def __call__(self, rst_file_content, must_raise=False, sphinxopts=None):
        index_rst = self.tmpdir.join("source").join("index.rst")
        index_rst.write(rst_file_content)

        cmd = ["sphinx-build", "-M", "doctest", "source", ""]
        if sphinxopts:
            cmd.append(sphinxopts)

        def to_str(subprocess_output):
            return "\n".join(subprocess_output.decode().splitlines())

        if must_raise:
            with pytest.raises(subprocess.CalledProcessError) as excinfo:
                subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            return to_str(excinfo.value.output)
        return to_str(subprocess.check_output(cmd))


@pytest.fixture
def sphinx_tester(tmpdir):
    with tmpdir.as_cwd():
        yield SphinxDoctestRunner(tmpdir)


def test_simple_doctest_failure(sphinx_tester):

    output = sphinx_tester(
        """
        ===!!!

        >>> 3 + 3
        5
        """,
        must_raise=True,
    )

    expected = textwrap.dedent(
        """
    Failed example:
        3 + 3
    Expected:
        5
    Got:
        6
    """
    )

    assert expected in output, "{!r}\n\n{!r}".format(expected, output)


def test_simple_doctest_success(sphinx_tester):
    output = sphinx_tester(
        """
        ===!!!

        >>> 3 + 3
        6
        """
    )
    assert "1 items passed all tests" in output


class TestDirectives:
    def test_testcode(self, testdir, sphinx_tester):
        code = """
            .. testcode::

                print("msg from testcode directive")

            .. testoutput::

                msg from testcode directive
            """

        sphinx_output = sphinx_tester(code)
        assert "1 items passed all tests" in sphinx_output

        plugin_result = testdir.runpytest("--doctest-glob=index.rst").stdout
        plugin_result.fnmatch_lines(["*=== 1 passed in *"])

    @pytest.mark.parametrize("raise_in_testcode", [True, False])
    def test_skipif_true(self, testdir, sphinx_tester, raise_in_testcode):
        code = """
            .. testcode::

                {}

            .. testoutput::
                :skipif: True

                NOT EVALUATED
            """.format(
            "raise RuntimeError" if raise_in_testcode else "pass"
        )

        sphinx_output = sphinx_tester(code, must_raise=raise_in_testcode)

        # -> ignore the testoutput section if skipif evaluates to True, but
        # -> always run the code in testcode
        plugin_output = testdir.runpytest("--doctest-glob=index.rst").stdout

        if raise_in_testcode:
            assert "1 failure in tests" in sphinx_output
            plugin_output.fnmatch_lines(["*=== 1 failed in *"])
        else:
            assert "1 items passed all tests" in sphinx_output
            plugin_output.fnmatch_lines(["*=== 1 passed in *"])

    @pytest.mark.parametrize(
        "testcode", ["raise RuntimeError", "pass", "print('EVALUATED')"]
    )
    def test_skipif_false(self, testdir, sphinx_tester, testcode):
        code = """
            .. testcode::

                {}

            .. testoutput::
                :skipif: False

                EVALUATED
            """.format(
            testcode
        )

        expected_failure = "EVALUATED" not in testcode

        sphinx_output = sphinx_tester(code, must_raise=expected_failure)
        plugin_output = testdir.runpytest("--doctest-glob=index.rst").stdout

        if expected_failure:
            assert "1 failure in tests" in sphinx_output
            plugin_output.fnmatch_lines(["*=== 1 failed in *"])
        else:
            assert "1 items passed all tests" in sphinx_output
            plugin_output.fnmatch_lines(["*=== 1 passed in *"])

    @pytest.mark.parametrize("wrong_output_assertion", [True, False])
    def test_skipif_multiple_testoutput(
        self, testdir, sphinx_tester, wrong_output_assertion
    ):
        # TODO add test, where there are muliple un-skipped testoutput
        # sections. IMO this must lead to a testfailure, which is currently
        # not the case in sphinx -> Create sphinx ticket
        code = """
            .. testcode::

                raise RuntimeError

            .. testoutput::
                :skipif: True

                NOT EVALUATED

            .. testoutput::
                :skipif: False

                Traceback (most recent call last):
                    ...
                {}
            """.format(
            "ValueError" if wrong_output_assertion else "RuntimeError"
        )

        # -> ignore all skipped testoutput sections, but use the one that is
        # -> not skipped

        sphinx_output = sphinx_tester(code, must_raise=wrong_output_assertion)

        plugin_output = testdir.runpytest("--doctest-glob=index.rst").stdout

        if wrong_output_assertion:
            assert "1 failure in tests" in sphinx_output
            plugin_output.fnmatch_lines(["*=== 1 failed in *"])
        else:
            assert "1 items passed all tests" in sphinx_output
            plugin_output.fnmatch_lines(["*=== 1 passed in *"])
