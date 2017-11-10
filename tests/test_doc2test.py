import doctest

from pytest_sphinx import docstring2test


def test_simple():
    doc = """
.. testcode::

    import pprint
    pprint.pprint({'3': 4, '5': 6})

.. testoutput::

    {'3': 4,
     '5': 6}
"""

    test = docstring2test(doc)
    assert len(test.examples) == 1
    example = test.examples[0]

    assert example.want == "{'3': 4,\n '5': 6}\n"
    assert example.exc_msg is None
    assert example.options == {}


def test_with_options():
    doc = """
.. testcode::

    import pprint
    pprint.pprint({'3': 4, '5': 6})

.. testoutput::
    :options: +NORMALIZE_WHITESPACE, +ELLIPSIS

    {'3': 4,
     '5': 6}"""

    test = docstring2test(doc)
    assert len(test.examples) == 1
    example = test.examples[0]

    assert example.want == "{'3': 4,\n '5': 6}\n"
    assert (docstring2test(doc + '\n').examples[0].want
            == "{'3': 4,\n '5': 6}\n")
    assert example.exc_msg is None
    assert example.options == {
        doctest.NORMALIZE_WHITESPACE: True,
        doctest.ELLIPSIS: True}
