# -*- coding: utf-8 -*-
"""
http://www.sphinx-doc.org/en/stable/ext/doctest.html
https://github.com/sphinx-doc/sphinx/blob/master/sphinx/ext/doctest.py

* TODO
** CLEANUP: use the sphinx directive parser from the sphinx project
"""

import doctest
import enum
import logging
import re
import sys
import textwrap
import traceback
from os import path

import _pytest.doctest
import docutils.frontend
import docutils.nodes
import docutils.parsers.rst
import docutils.utils
import pytest
from _pytest.doctest import DoctestItem
from docutils import nodes
from docutils.parsers.rst import directives

logger = logging.getLogger(__name__)


blankline_re = re.compile(r"^\s*<BLANKLINE>", re.MULTILINE)
doctestopt_re = re.compile(r"#\s*doctest:.+$", re.MULTILINE)


class SphinxDoctestDirectives(enum.Enum):
    TESTCODE = 1
    TESTOUTPUT = 2
    TESTSETUP = 3
    TESTCLEANUP = 4
    DOCTEST = 5


def pytest_collect_file(path, parent):
    config = parent.config
    if path.ext == ".py":
        if config.option.doctestmodules:
            if hasattr(SphinxDoctestModule, "from_parent"):
                return SphinxDoctestModule.from_parent(parent, fspath=path)
            else:
                return SphinxDoctestModule(path, parent)
    elif _is_doctest(config, path, parent):
        if hasattr(SphinxDoctestTextfile, "from_parent"):
            return SphinxDoctestTextfile.from_parent(parent, fspath=path)
        else:
            return SphinxDoctestTextfile(path, parent)


def _is_doctest(config, path, parent):
    if path.ext in (".txt", ".rst") and parent.session.isinitpath(path):
        return True
    globs = config.getoption("doctestglob") or ["test*.txt"]
    for glob in globs:
        if path.check(fnmatch=glob):
            return True
    return False


def _get_next_textoutputsections(sections, index):
    """Yield successive TESTOUTPUT sections."""
    for j in range(index, len(sections)):
        section = sections[j]
        if section.directive == SphinxDoctestDirectives.TESTOUTPUT:
            yield section
        else:
            break


class Section:
    def __init__(self, directive, body, skipif_expr, options, lineno, groups):
        self.directive = directive
        self.body = body
        self.skipif_expr = skipif_expr
        self.options = options
        self.lineno = lineno
        self.groups = groups


class TestDirective(docutils.parsers.rst.Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True

    def run(self):
        print(f"Run called {self.__class__.__name__}")
        code = "\n".join(self.content)
        test = None
        if self.name == "doctest":
            if "<BLANKLINE>" in code:
                # convert <BLANKLINE>s to ordinary blank lines for presentation
                test = code
                code = blankline_re.sub("", code)
            if doctestopt_re.search(code):
                if not test:
                    test = code
                code = doctestopt_re.sub("", code)
        nodetype = nodes.literal_block  # type: Type[TextElement]
        if self.name in ("testsetup", "testcleanup") or "hide" in self.options:
            nodetype = nodes.comment
        if self.arguments:
            groups = [x.strip() for x in self.arguments[0].split(",")]
        else:
            groups = ["default"]

        node = nodetype(code, code, testnodetype=self.name, groups=groups)
        node["options"] = {}
        if (
            self.name in ("doctest", "testoutput")
            and "options" in self.options
        ):
            # parse doctest-like output comparison flags
            option_strings = self.options["options"].replace(",", " ").split()
            for option in option_strings:
                prefix, option_name = option[0], option[1:]
                if prefix not in "+-":
                    self.state.document.reporter.warning(
                        "missing '+' or '-' in '%s' option." % option,
                        line=self.lineno,
                    )
                    continue
                if option_name not in doctest.OPTIONFLAGS_BY_NAME:
                    self.state.document.reporter.warning(
                        "'%s' is not a valid option." % option_name,
                        line=self.lineno,
                    )
                    continue
                flag = doctest.OPTIONFLAGS_BY_NAME[option[1:]]
                node["options"][flag] = option[0] == "+"
        # if self.name == 'doctest' and 'pyversion' in self.options:
        #     try:
        #         spec = self.options['pyversion']
        #         python_version = '.'.join([str(v) for v in sys.version_info[:3]])
        #         if not is_allowed_version(spec, python_version):
        #             flag = doctest.OPTIONFLAGS_BY_NAME['SKIP']
        #             node['options'][flag] = True  # Skip the test
        #     except InvalidSpecifier:
        #         self.state.document.reporter.warning(
        #             __("'%s' is not a valid pyversion option") % spec,
        #             line=self.lineno)
        if "skipif" in self.options:
            node["skipif"] = self.options["skipif"]
        return [node]


class TestsetupDirective(TestDirective):
    option_spec = {"skipif": directives.unchanged_required}


class TestcleanupDirective(TestDirective):
    option_spec = {"skipif": directives.unchanged_required}


class DoctestDirective(TestDirective):
    option_spec = {
        "hide": directives.flag,
        "options": directives.unchanged,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
    }


class TestcodeDirective(TestDirective):
    option_spec = {
        "hide": directives.flag,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
    }


class TestoutputDirective(TestDirective):
    option_spec = {
        "hide": directives.flag,
        "options": directives.unchanged,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
    }


directives.register_directive("testcode", TestcodeDirective)
directives.register_directive("testoutput", TestoutputDirective)
directives.register_directive("testsetup", TestsetupDirective)
directives.register_directive("testcleanup", TestcleanupDirective)
directives.register_directive("doctest", DoctestDirective)


def parse_rst(text: str) -> docutils.nodes.document:
    parser = docutils.parsers.rst.Parser()
    components = (docutils.parsers.rst.Parser,)
    settings = docutils.frontend.OptionParser(
        components=components
    ).get_default_values()
    document = docutils.utils.new_document("<rst-doc>", settings=settings)
    parser.parse(text, document)
    return document


def condition(node):
    return (
        isinstance(node, (nodes.literal_block, nodes.comment))
        and "testnodetype" in node
    )


def get_line_number(node):
    """Get the real line number or admit we don't know."""
    # FIXME since the directives in a docstring are indented (except in a
    # module docstring), the line numbers are 0 (Can this be fixed somehow?)

    if ":docstring of " in path.basename(node.source or ""):
        return 0
    if node.line is not None:
        return node.line - 1
    return 0


def get_sections(docstring):
    doctree = parse_rst(docstring)

    sections = []
    for node in doctree.traverse(condition):  # type: Element
        # if self.skipped(node):
        #     continue
        print(node.__class__.__name__)
        # pprint.pprint(node.__dict__)

        source = node["test"] if "test" in node else node.astext()
        # lines = source.splitlines()
        # filename = self.get_filename_for_node(node, docname)
        # line_number = self.get_line_number(node)
        node_type = node.get("testnodetype", "doctest")
        node_type = getattr(SphinxDoctestDirectives, node_type.upper())
        node_options = node.get("options")
        node_groups = node.get("groups", ["default"])
        line_number = get_line_number(node)
        node_skipif = node.get("skipif")
        print(
            f"Node: {node_type} {node_options} {node_groups} {line_number} "
            f": {source}"
        )
        sections.append(
            Section(
                node_type,
                source,
                node_skipif,
                node_options,
                line_number,
                node_groups,
            )
        )

    return sections


def docstring2examples(docstring, globs=None):
    """
    Parse all sphinx test directives in the docstring and create a
    list of examples.
    """
    # TODO pass additional lineno to docstring2examples?
    # TODO subclass doctest.DocTestParser instead?

    if not globs:
        globs = {}

    sections = get_sections(docstring)

    def get_testoutput_section_data(section):
        want = section.body
        exc_msg = None
        options = {}

        if section.skipif_expr and eval(section.skipif_expr, globs):
            want = ""
        else:
            options = section.options
            match = doctest.DocTestParser._EXCEPTION_RE.match(want)
            if match:
                exc_msg = match.group("msg")

        return want, options, section.lineno, exc_msg

    examples = []
    for i, current_section in enumerate(sections):
        if current_section.directive == SphinxDoctestDirectives.TESTCODE:
            next_testoutput_sections = _get_next_textoutputsections(
                sections, i + 1
            )
            section_data_seq = [
                get_testoutput_section_data(s)
                for s in next_testoutput_sections
            ]

            num_unskipped_sections = len([d for d in section_data_seq if d[0]])
            if num_unskipped_sections > 1:
                raise ValueError(
                    "There are multiple unskipped TESTOUTPUT sections"
                )

            if num_unskipped_sections:
                want, options, _, exc_msg = next(
                    d for d in section_data_seq if d[0]
                )
            else:
                # no unskipped testoutput section
                # do we really need doctest.Example to test
                # independent TESTCODE sections?
                want, options, exc_msg = (
                    "",
                    {},
                    None,
                )

            if current_section.skipif_expr and eval(
                current_section.skipif_expr, globs
            ):
                # TODO add the doctest.Example to `examples` but mark it as
                # skipped.
                continue

            # the lineno used here is used for exceptions:
            # it is the number of lines starting one line
            # before e.g. the testcode directive until the
            # end of the body of that directive.
            examples.append(
                doctest.Example(
                    source=current_section.body,
                    want=want,
                    exc_msg=exc_msg,
                    # we want to see the ..testcode lines in the
                    # console output but not the ..testoutput
                    # lines
                    # TODO why do we want to hide testoutput??
                    lineno=current_section.lineno - 1,
                    options=options,
                )
            )
    return examples


class SphinxDocTestRunner(doctest.DebugRunner):
    """
    overwrite doctest.DocTestRunner.__run, since it uses 'single' for the
    `compile` function instead of 'exec'.
    """

    def _DocTestRunner__run(self, test, compileflags, out):
        """
        Run the examples in `test`.

        Write the outcome of each example with one of the
        `DocTestRunner.report_*` methods, using the writer function
        `out`.  `compileflags` is the set of compiler flags that should
        be used to execute examples.  Return a tuple `(f, t)`, where `t`
        is the number of examples tried, and `f` is the number of
        examples that failed.  The examples are run in the namespace
        `test.globs`.

        """
        # Keep track of the number of failures and tries.
        failures = tries = 0

        # Save the option flags (since option directives can be used
        # to modify them).
        original_optionflags = self.optionflags

        SUCCESS, FAILURE, BOOM = range(3)  # `outcome` state

        check = self._checker.check_output

        # Process each example.
        for examplenum, example in enumerate(test.examples):

            # If REPORT_ONLY_FIRST_FAILURE is set, then suppress
            # reporting after the first failure.
            quiet = (
                self.optionflags & doctest.REPORT_ONLY_FIRST_FAILURE
                and failures > 0
            )

            # Merge in the example's options.
            self.optionflags = original_optionflags
            if example.options:
                for (optionflag, val) in example.options.items():
                    if val:
                        self.optionflags |= optionflag
                    else:
                        self.optionflags &= ~optionflag

            # If 'SKIP' is set, then skip this example.
            if self.optionflags & doctest.SKIP:
                continue

            # Record that we started this example.
            tries += 1
            if not quiet:
                self.report_start(out, test, example)

            # Use a special filename for compile(), so we can retrieve
            # the source code during interactive debugging (see
            # __patched_linecache_getlines).
            filename = "<doctest %s[%d]>" % (test.name, examplenum)

            # Run the example in the given context (globs), and record
            # any exception that gets raised.  (But don't intercept
            # keyboard interrupts.)
            try:
                # Don't blink!  This is where the user's code gets run.
                exec(
                    compile(example.source, filename, "exec", compileflags, 1),
                    test.globs,
                )
                self.debugger.set_continue()  # ==== Example Finished ====
                exception = None
            except KeyboardInterrupt:
                raise
            except Exception:
                exception = sys.exc_info()
                self.debugger.set_continue()  # ==== Example Finished ====

            got = self._fakeout.getvalue()  # the actual output
            self._fakeout.truncate(0)
            outcome = FAILURE  # guilty until proved innocent or insane

            # If the example executed without raising any exceptions,
            # verify its output.
            if exception is None:
                if check(example.want, got, self.optionflags):
                    outcome = SUCCESS

            # The example raised an exception:  check if it was expected.
            else:
                exc_msg = traceback.format_exception_only(*exception[:2])[-1]
                if not quiet:
                    got += doctest._exception_traceback(exception)

                # If `example.exc_msg` is None, then we weren't expecting
                # an exception.
                if example.exc_msg is None:
                    outcome = BOOM

                # We expected an exception:  see whether it matches.
                elif check(example.exc_msg, exc_msg, self.optionflags):
                    outcome = SUCCESS

                # Another chance if they didn't care about the detail.
                elif self.optionflags & doctest.IGNORE_EXCEPTION_DETAIL:
                    if check(
                        doctest._strip_exception_details(example.exc_msg),
                        doctest._strip_exception_details(exc_msg),
                        self.optionflags,
                    ):
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
                    self.report_unexpected_exception(
                        out, test, example, exception
                    )
                failures += 1
            else:
                assert False, ("unknown outcome", outcome)

            if failures and self.optionflags & doctest.FAIL_FAST:
                break

        # Restore the option flags (in case they were modified)
        self.optionflags = original_optionflags

        # Record and return the number of failures and tries.
        self._DocTestRunner__record_outcome(test, failures, tries)
        return doctest.TestResults(failures, tries)


class SphinxDocTestParser(object):
    def get_doctest(self, docstring, globs, name, filename, lineno):
        # TODO document why we need to overwrite? get_doctest
        return doctest.DocTest(
            examples=docstring2examples(textwrap.dedent(docstring), globs=globs),
            globs=globs,
            name=name,
            filename=filename,
            lineno=lineno,
            docstring=docstring,
        )


class SphinxDoctestTextfile(pytest.Module):
    obj = None

    def collect(self):
        # inspired by doctest.testfile; ideally we would use it directly,
        # but it doesn't support passing a custom checker
        encoding = self.config.getini("doctest_encoding")
        text = self.fspath.read_text(encoding)
        name = self.fspath.basename

        optionflags = _pytest.doctest.get_optionflags(self)
        runner = SphinxDocTestRunner(
            verbose=0,
            optionflags=optionflags,
            checker=_pytest.doctest._get_checker(),
        )

        test = doctest.DocTest(
            examples=docstring2examples(text),
            globs={},
            name=name,
            filename=name,
            lineno=0,
            docstring=text,
        )

        if test.examples:
            if hasattr(DoctestItem, "from_parent"):
                yield DoctestItem.from_parent(
                    parent=self, name=test.name, runner=runner, dtest=test
                )
            else:
                yield DoctestItem(test.name, self, runner, test)


class SphinxDoctestModule(pytest.Module):
    def collect(self):
        if self.fspath.basename == "conftest.py":
            module = self.config.pluginmanager._importconftest(self.fspath)
        else:
            try:
                module = self.fspath.pyimport()
            except ImportError:
                if self.config.getvalue("doctest_ignore_import_errors"):
                    pytest.skip("unable to import module %r" % self.fspath)
                else:
                    raise
        optionflags = _pytest.doctest.get_optionflags(self)

        class MockAwareDocTestFinder(doctest.DocTestFinder):
            """
            a hackish doctest finder that overrides stdlib internals to fix
            a stdlib bug
            https://github.com/pytest-dev/pytest/issues/3456
            https://bugs.python.org/issue25532

            fix taken from https://github.com/pytest-dev/pytest/pull/4212/
            """

            def _find(
                self, tests, obj, name, module, source_lines, globs, seen
            ):
                if _is_mocked(obj):
                    return
                with _patch_unwrap_mock_aware():
                    doctest.DocTestFinder._find(
                        self,
                        tests,
                        obj,
                        name,
                        module,
                        source_lines,
                        globs,
                        seen,
                    )

        try:
            from _pytest.doctest import _is_mocked
            from _pytest.doctest import _patch_unwrap_mock_aware
        except ImportError:
            finder = doctest.DocTestFinder(parser=SphinxDocTestParser())
        else:
            finder = MockAwareDocTestFinder(parser=SphinxDocTestParser())

        runner = SphinxDocTestRunner(
            verbose=0,
            optionflags=optionflags,
            checker=_pytest.doctest._get_checker(),
        )

        for test in finder.find(module, module.__name__):
            if test.examples:
                if hasattr(DoctestItem, "from_parent"):
                    yield DoctestItem.from_parent(
                        parent=self, name=test.name, runner=runner, dtest=test
                    )
                else:
                    yield DoctestItem(test.name, self, runner, test)
