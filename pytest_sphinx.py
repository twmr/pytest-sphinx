# -*- coding: utf-8 -*-
"""

http://www.sphinx-doc.org/en/stable/ext/doctest.html
https://github.com/sphinx-doc/sphinx/blob/master/sphinx/ext/doctest.py

* TODO
** find all docstrings in python files
** search for sphinx directives in the docstrings
** create Example objects which contain the source, expected output, setup code, cleanup_code
** create a custom Example class, which only has methods, which are needed by the runner object.
*** DocTestRunner(verbose=False)
*** the example class needs the following attrs
*** want, source, lineno (zero indexed) - hardcode it to zero, set 'options' to {}
** TODO overwrite DocTestRunner.__run, since it passes the 'single' str to compile().


* CLEANUP
** use the sphinx directive parser from the sphinx project


doctestoptions


.. testcode::

   1+1        # this will give no output!
   print(2+2) # this will give output

.. testoutput::
   3

"""

import doctest
import _pytest.doctest
import pytest


def pytest_addoption(parser):
    group = parser.getgroup('sphinx')
    group.addoption(
        '--foo',
        action='store',
        dest='dest_foo',
        default='2017',
        help='Set # TODO:he value for the fixture "bar".'
    )

    parser.addini('HELLO', 'Dummy pytest.ini setting')


def pytest_collect_file(path, parent):
    config = parent.config
    # print(path)
    if path.ext == ".py":
        if config.option.doctestmodules:
            return SphinxDoctestModule(path, parent)
    # elif _is_doctest(config, path, parent):
    #     return DoctestTextfile(path, parent)


def _is_doctest(config, path, parent):
    if path.ext in ('.txt', '.rst') and parent.session.isinitpath(path):
        return True
    globs = config.getoption("doctestglob") or ['test*.txt']
    for glob in globs:
        if path.check(fnmatch=glob):
            return True
    return False


def docstring2test(docstring, lineno):
    import re
    import enum
    import itertools
    import textwrap


    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = itertools.tee(iterable)
        next(b, None)
        return itertools.izip(a, b)

    class DoctestDirectives(enum.Enum):
        CODE = 1
        OUTPUT = 2
        SETUP = 3
        CLEANUP = 4

    class Test(object):
        def __init__(self, examples):
            self.examples = examples
            self.globs = {}
            self.name = 'mytest'
            self.lineno = lineno
            self.filename = 'dummyfilename'
            self.docstring = docstring

    lines = textwrap.dedent(docstring).splitlines()
    matches = [i for i, line in enumerate(lines) if
               any(line.startswith('.. test' + d.name.lower() + '::')
                   for d in DoctestDirectives)]
    if not matches:
        return Test([])

    matches.append(len(lines))

    class Section:
        def __init__(self, name, content, lineno):
            self.name = name
            self.lineno = lineno
            if name in (DoctestDirectives.CODE, DoctestDirectives.OUTPUT):
                # remove empty lines
                filtered = filter(lambda x: not re.match(r'^\s*$', x),
                                  content.splitlines())
                self.content = '\n'.join(filtered)
            else:
                self.content = content

    def is_empty_of_indented(line):
        return not line or line.startswith('   ')

    sections = []
    for x, y in pairwise(matches):
        section = lines[x:y]
        header = section[0]
        directive = next(d for d in DoctestDirectives
                         if 'test' + d.name.lower() in header)
        out = '\n'.join(itertools.takewhile(
            is_empty_of_indented, section[1:]))
        sections.append(Section(
            directive,
            textwrap.dedent(out),
            lineno=x))

    examples = []
    for x, y in pairwise(sections):
        # TODO support DoctestDirectives.SETUP, ...
        if (x.name == DoctestDirectives.CODE and
                y.name == DoctestDirectives.OUTPUT):
            examples.append(
                doctest.Example(source=x.content, want=y.content,
                                # we want to see the ..testcode lines in the
                                # console output but not the ..testoutput
                                # lines
                                lineno=y.lineno - 1))

    return Test(examples)


class SphinxDocTestRunner(doctest.DebugRunner):
    """
    overwrite doctest.DocTestRunner.__run, since it uses 'single' for the
    `compile` function instead of
    """
    def __run(self, test, compileflags, out):
        """
        Run the examples in `test`.  Write the outcome of each example
        with one of the `DocTestRunner.report_*` methods, using the
        writer function `out`.  `compileflags` is the set of compiler
        flags that should be used to execute examples.  Return a tuple
        `(f, t)`, where `t` is the number of examples tried, and `f`
        is the number of examples that failed.  The examples are run
        in the namespace `test.globs`.
        """
        # Keep track of the number of failures and tries.
        failures = tries = 0

        # Save the option flags (since option directives can be used
        # to modify them).
        original_optionflags = self.optionflags

        SUCCESS, FAILURE, BOOM = range(3) # `outcome` state

        check = self._checker.check_output

        # Process each example.
        for examplenum, example in enumerate(test.examples):

            # If REPORT_ONLY_FIRST_FAILURE is set, then suppress
            # reporting after the first failure.
            quiet = (self.optionflags & REPORT_ONLY_FIRST_FAILURE and
                     failures > 0)

            # Merge in the example's options.
            self.optionflags = original_optionflags
            if example.options:
                for (optionflag, val) in example.options.items():
                    if val:
                        self.optionflags |= optionflag
                    else:
                        self.optionflags &= ~optionflag

            # If 'SKIP' is set, then skip this example.
            if self.optionflags & SKIP:
                continue

            # Record that we started this example.
            tries += 1
            if not quiet:
                self.report_start(out, test, example)

            # Use a special filename for compile(), so we can retrieve
            # the source code during interactive debugging (see
            # __patched_linecache_getlines).
            filename = '<doctest %s[%d]>' % (test.name, examplenum)

            # Run the example in the given context (globs), and record
            # any exception that gets raised.  (But don't intercept
            # keyboard interrupts.)
            try:
                # Don't blink!  This is where the user's code gets run.
                exec(compile(example.source, filename, "exec",
                             compileflags, 1), test.globs)
                self.debugger.set_continue()  # ==== Example Finished ====
                exception = None
            except KeyboardInterrupt:
                raise
            except:
                exception = sys.exc_info()
                self.debugger.set_continue()  # ==== Example Finished ====

            got = self._fakeout.getvalue()  # the actual output
            self._fakeout.truncate(0)
            outcome = FAILURE   # guilty until proved innocent or insane

            # If the example executed without raising any exceptions,
            # verify its output.
            if exception is None:
                if check(example.want, got, self.optionflags):
                    outcome = SUCCESS

            # The example raised an exception:  check if it was expected.
            else:
                exc_msg = traceback.format_exception_only(*exception[:2])[-1]
                if not quiet:
                    got += _exception_traceback(exception)

                # If `example.exc_msg` is None, then we weren't expecting
                # an exception.
                if example.exc_msg is None:
                    outcome = BOOM

                # We expected an exception:  see whether it matches.
                elif check(example.exc_msg, exc_msg, self.optionflags):
                    outcome = SUCCESS

                # Another chance if they didn't care about the detail.
                elif self.optionflags & IGNORE_EXCEPTION_DETAIL:
                    if check(_strip_exception_details(example.exc_msg),
                             _strip_exception_details(exc_msg),
                             self.optionflags):
                        outcome = SUCCESS

            # Report the outcome.
            if outcome is SUCCESS:
                if not quiet:
                    self.report_success(out, test, example, got)
            elif outcome is FAILURE:
                if not quiet:
                    self.report_failure(out, test, example, got)
                failures += 1
            elif outcome is BOOM:
                if not quiet:
                    self.report_unexpected_exception(out, test, example,
                                                     exception)
                failures += 1
            else:
                assert False, ("unknown outcome", outcome)

            if failures and self.optionflags & FAIL_FAST:
                break

        # Restore the option flags (in case they were modified)
        self.optionflags = original_optionflags

        # Record and return the number of failures and tries.
        self.__record_outcome(test, failures, tries)
        return doctest.TestResults(failures, tries)


class SphinxDoctestModule(pytest.Module):
    def collect(self):
        if self.fspath.basename == "conftest.py":
            module = self.config.pluginmanager._importconftest(self.fspath)
        else:
            try:
                module = self.fspath.pyimport()
            except ImportError:
                if self.config.getvalue('doctest_ignore_import_errors'):
                    pytest.skip('unable to import module %r' % self.fspath)
                else:
                    raise

        class SphinxDocTestParser:
            def get_doctest(self, docstring, globs, name, filename, lineno):
                # todo create objects for each sphinx collective
                print(filename, lineno)
                return docstring, lineno

        finder = doctest.DocTestFinder(parser=SphinxDocTestParser())
        # optionflags = get_optionflags(self)
        runner = SphinxDocTestRunner(verbose=0)

        for docstring, lineno in finder.find(module, module.__name__):
            test = docstring2test(docstring, lineno)
            if test.examples:
                yield _pytest.doctest.DoctestItem(
                    test.name, self, runner, test)
