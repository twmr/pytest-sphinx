import doctest
import os
import textwrap

import pytest

from pytest_sphinx import docstring2examples
from pytest_sphinx import get_sections


@pytest.mark.parametrize("in_between_content", ["", "some text\nmore text"])
def test_simple(in_between_content):
    doc = """
.. testcode::

    import pprint
    pprint.pprint({'3': 4, '5': 6})

{}
.. testoutput::

    {'3': 4,
     '5': 6}
""".format(
        in_between_content
    )

    examples = docstring2examples(doc)
    assert len(examples) == 1
    example = examples[0]

    assert example.want == "{'3': 4,\n '5': 6}\n"
    assert example.exc_msg is None
    assert example.options == {}
    assert example.lineno == 5


def test_with_options():
    doc = """
.. testcode::

    import pprint
    pprint.pprint({'3': 4, '5': 6})

.. testoutput::
    :options: +NORMALIZE_WHITESPACE, +ELLIPSIS

    {'3': 4,
     '5': 6}"""

    examples = docstring2examples(doc)
    assert len(examples) == 1
    example = examples[0]

    assert example.want == "{'3': 4,\n '5': 6}\n"
    assert docstring2examples(doc + "\n")[0].want == "{'3': 4,\n '5': 6}\n"
    assert example.exc_msg is None
    assert example.options == {
        doctest.NORMALIZE_WHITESPACE: True,
        doctest.ELLIPSIS: True,
    }
    assert example.lineno == 5


def test_indented():
    doc = textwrap.dedent(
        """
    Examples:
        some text

        .. testcode::

            print("Banana")

        .. testoutput::

            Banana
    """
    )

    examples = docstring2examples(doc)
    assert len(examples) == 1
    example = examples[0]

    assert example.want == "Banana\n"
    assert example.exc_msg is None
    assert example.options == {}
    assert example.lineno == 7


def test_cartopy():
    rstpath = os.path.join(
        os.path.dirname(__file__), "testdata", "using_the_shapereader.rst"
    )
    with open(rstpath, "r") as fh:
        sections = get_sections(fh.read())

    assert len(sections) == 9
