doctest examples
================

Plain-old `doctest_block`
-------------------------

>>> print(f'this is a doctest block: 2 + 2 = {2 + 2}')
this is a doctest block: 2 + 2 = 4

They end with a blank line

sphinx.ext.doctest-like directives (basic)
------------------------------------------

.. doctest::

    >>> 2 + 2
    4

.. doctest:: Our example

    >>> round(
    ...     3.9
    ... )
    4

.. doctest:: Here's a function

    >>> def shout(message: str) -> str:
    ...     print(f'{message.upper()}')

    >>> shout('hello')
    HELLO
