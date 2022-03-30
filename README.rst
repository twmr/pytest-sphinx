=============
pytest-sphinx
=============

.. image:: https://github.com/thisch/pytest-sphinx/workflows/Test/badge.svg
    :target: https://github.com/thisch/pytest-sphinx/actions
    :alt: Action Status

A doctest plugin for pytest, which understands the sphinx-specific
directives from `doctest-sphinx`_. Those sphinx-specific directives can be
used in rst files as well as in docstrings of python modules.


Features
--------

* support for ``testcode`` and ``testoutput`` directives
* support for ``testsetup`` and ``testcleanup`` is planned (pull-requests welcome)
* support for parsing global optionflags (``doctest_optionflags``) from
  ``pytest.ini``
* support for ``:options:`` in ``testoutput``
* support for ``:skipif:`` in ``testcode`` and in ``testoutput``
* ``:hide:`` is ignored by "pytest-sphinx"


Requirements
------------

* pytest


Installation
------------

You can install "pytest-sphinx" via `pip`_ from `PyPI`_::

    $ pip install pytest-sphinx


Usage
-----

* See `doctest-sphinx`_. Have a look at the examples in `doctest-examples`_.
* Run pytest with the `--doctest-modules` flag.


Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.


License
-------

Distributed under the terms of the `BSD-3`_ license, "pytest-sphinx" is free and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`doctest-sphinx`: http://www.sphinx-doc.org/en/stable/ext/doctest.html
.. _`doctest-examples`: https://github.com/sphinx-doc/sphinx/blob/master/tests/roots/test-ext-doctest/doctest.txt
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`BSD-3`: http://opensource.org/licenses/BSD-3-Clause
.. _`GNU GPL v3.0`: http://www.gnu.org/licenses/gpl-3.0.txt
.. _`Apache Software License 2.0`: http://www.apache.org/licenses/LICENSE-2.0
.. _`file an issue`: https://github.com/thisch/pytest-sphinx/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.python.org/pypi/pip/
.. _`PyPI`: https://pypi.python.org/pypi
