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

        if must_raise:
            with pytest.raises(subprocess.CalledProcessError) as excinfo:
                subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            return excinfo.value.output.decode()
        return subprocess.check_output(cmd).decode()


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

    assert expected in output, output


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
    def test_testcode(self, sphinx_tester):
        code = """
            .. testcode::

                print("msg from testcode directive")

            .. testoutput::

                msg from testcode directive
            """

        output = sphinx_tester(code)
        assert "1 items passed all tests" in output

    @pytest.mark.parametrize("raise_in_testcode", [True, False])
    def test_skipif(self, sphinx_tester, raise_in_testcode):
        code = """
            .. testcode::

                {}

            .. testoutput::
                :skipif: True

                NOT EVALUATED
            """.format(
            "raise RuntimeError" if raise_in_testcode else "pass"
        )

        output = sphinx_tester(code, must_raise=raise_in_testcode)

        if raise_in_testcode:
            assert "1 failure in tests" in output
        else:
            assert "1 items passed all tests" in output
