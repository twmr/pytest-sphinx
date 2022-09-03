import doctest
import linecache
import logging
import os
import pathlib
import pprint
import re
import sys
import types
import typing as t

import docutils
from docutils import nodes
from docutils.nodes import Node
from docutils.nodes import TextElement
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives
from packaging.specifiers import InvalidSpecifier
from packaging.specifiers import SpecifierSet
from packaging.version import Version

logger = logging.getLogger(__name__)


blankline_re = re.compile(r"^\s*<BLANKLINE>", re.MULTILINE)
doctestopt_re = re.compile(r"#\s*doctest:.+$", re.MULTILINE)

OptionSpec = t.Dict[str, t.Callable[[str], t.Any]]


def is_allowed_version(spec: str, version: str) -> bool:
    """Check `spec` satisfies `version` or not.
    This obeys PEP-440 specifiers:
    https://peps.python.org/pep-0440/#version-specifiers
    Some examples:
        >>> is_allowed_version('3.3', '<=3.5')
        True
        >>> is_allowed_version('3.3', '<=3.2')
        False
        >>> is_allowed_version('3.3', '>3.2, <4.0')
        True
    """
    return Version(version) in SpecifierSet(spec)


class TestDirective(Directive):
    """
    Base class for doctest-related directives.
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True

    def get_source_info(self) -> t.Tuple[str, int]:
        """Get source and line number."""
        return self.state_machine.get_source_and_line(self.lineno)  # type: ignore

    def set_source_info(self, node: Node) -> None:
        """Set source and line number to the node."""
        node.source, node.line = self.get_source_info()

    def run(self) -> t.List[Node]:
        # use ordinary docutils nodes for test code: they get special attributes
        # so that our builder recognizes them, and the other builders are happy.
        code = "\n".join(self.content)
        test = None

        logger.debug(f"directive run: self.name {self.name}")
        if self.name == "doctest":
            if "<BLANKLINE>" in code:
                # convert <BLANKLINE>s to ordinary blank lines for presentation
                test = code
                code = blankline_re.sub("", code)
            if (
                doctestopt_re.search(code)
                and "no-trim-doctest-flags" not in self.options
            ):
                if not test:
                    test = code
                code = doctestopt_re.sub("", code)
        nodetype: t.Type[TextElement] = nodes.literal_block
        if self.name in ("testsetup", "testcleanup") or "hide" in self.options:
            nodetype = nodes.comment
        if self.arguments:
            groups = [x.strip() for x in self.arguments[0].split(",")]
        else:
            groups = ["default"]
        node = nodetype(code, code, testnodetype=self.name, groups=groups)
        self.set_source_info(node)
        if test is not None:
            # only save if it differs from code
            node["test"] = test
        if self.name == "doctest":
            node["language"] = "pycon3"
        node["options"] = {}
        if self.name in ("doctest") and "options" in self.options:
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
        if self.name == "doctest" and "pyversion" in self.options:
            try:
                spec = self.options["pyversion"]
                python_version = ".".join([str(v) for v in sys.version_info[:3]])
                if not is_allowed_version(spec, python_version):
                    flag = doctest.OPTIONFLAGS_BY_NAME["SKIP"]
                    node["options"][flag] = True  # Skip the test
            except InvalidSpecifier:
                self.state.document.reporter.warning(
                    "'%s' is not a valid pyversion option" % spec, line=self.lineno
                )
        if "skipif" in self.options:
            node["skipif"] = self.options["skipif"]
        if "trim-doctest-flags" in self.options:
            node["trim_flags"] = True
        elif "no-trim-doctest-flags" in self.options:
            node["trim_flags"] = False
        return [node]


class TestsetupDirective(TestDirective):
    option_spec: OptionSpec = {"skipif": directives.unchanged_required}


class TestcleanupDirective(TestDirective):
    option_spec: OptionSpec = {"skipif": directives.unchanged_required}


class DoctestDirective(TestDirective):
    option_spec: OptionSpec = {
        "hide": directives.flag,
        "no-trim-doctest-flags": directives.flag,
        "options": directives.unchanged,
        "pyversion": directives.unchanged_required,
        "skipif": directives.unchanged_required,
        "trim-doctest-flags": directives.flag,
    }


def setup() -> t.Dict[str, t.Any]:
    directives.register_directive("testsetup", TestsetupDirective)
    directives.register_directive("testcleanup", TestcleanupDirective)
    directives.register_directive("doctest", DoctestDirective)
    return {"version": docutils.__version__, "parallel_read_safe": True}


# For backward compatibility, a global instance of a DocTestRunner
# class, updated by testmod.
master = None

parser = doctest.DocTestParser()


class DocutilsDocTestFinder:
    """
    A class used to extract the DocTests that are relevant to a given
    docutils file. Doctests can be extracted from the followwing directive
    types: doctest_block (doctest), DocTestDirective. Myst-parser is also
    supported for parsing markdown files.
    """

    def __init__(
        self,
        verbose: bool = False,
        parser: "doctest.DocTestParser" = parser,
    ):
        """
        Create a new doctest finder.

        The optional argument `parser` specifies a class or
        function that should be used to create new DocTest objects (or
        objects that implement the same interface as DocTest).  The
        signature for this factory function should match the signature
        of the DocTest constructor.
        """
        self._parser = parser
        self._verbose = verbose

    def find(
        self,
        string: str,
        name: t.Optional[str] = None,
        globs: t.Optional[t.Dict[str, t.Any]] = None,
        extraglobs: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> t.List[doctest.DocTest]:
        """
        Return a list of the DocTests that are defined by the given
        string (its parsed directives).

        The globals for each DocTest is formed by combining `globs`
        and `extraglobs` (bindings in `extraglobs` override bindings
        in `globs`).  A new copy of the globals dictionary is created
        for each DocTest.  If `globs` is not specified, then it
        defaults to the module's `__dict__`, if specified, or {}
        otherwise.  If `extraglobs` is not specified, then it defaults
        to {}.

        """
        # If name was not specified, then extract it from the string.
        if name is None:
            name = getattr(string, "__name__", None)
            if name is None:
                raise ValueError(
                    "DocTestFinder.find: name must be given "
                    "when string.__name__ doesn't exist: %r" % (type(string),)
                )

        # No access to a loader, so assume it's a normal
        # filesystem path
        source_lines = linecache.getlines(name) or None
        if not source_lines:
            source_lines = None

        # Initialize globals, and merge in extraglobs.
        if globs is None:
            globs = {}
        else:
            globs = globs.copy()
        if extraglobs is not None:
            globs.update(extraglobs)
        if "__name__" not in globs:
            globs["__name__"] = "__main__"  # provide a default module name

        tests: t.List[doctest.DocTest] = []
        self._find(tests, string, name, source_lines, globs, {}, name)
        # Sort the tests by alpha order of names, for consistency in
        # verbose-mode output.  This was a feature of doctest in Pythons
        # <= 2.3 that got lost by accident in 2.4.  It was repaired in
        # 2.4.4 and 2.5.
        tests.sort()
        return tests

    def _find(
        self,
        tests: t.List[doctest.DocTest],
        string: str,
        name: str,
        source_lines: t.Optional[t.List[str]],
        globs: t.Dict[str, t.Any],
        seen: t.Dict[int, int],
        source_path: t.Optional[pathlib.Path] = None,
    ) -> None:
        """
        Find tests for the given string, and add them to `tests`.
        """
        if self._verbose:
            print("Finding tests in %s" % name)

        # If we've already processed this string, then ignore it.
        if id(string) in seen:
            return
        seen[id(string)] = 1

        # Find a test for this string, and add it to the list of tests.
        logger.debug(
            "_find(%s)"
            % pprint.pformat(
                {
                    "tests": tests,
                    "string": string,
                    "name": name,
                    "source_lines": source_lines,
                    "globs": globs,
                    "seen": seen,
                }
            )
        )
        ext = pathlib.Path(name).suffix
        logger.debug(f"parse, ext: {ext}")
        if ext == ".md":
            import myst_parser.parsers.docutils_
            from myst_parser.config.main import MdParserConfig
            from myst_parser.mdit_to_docutils.base import DocutilsRenderer
            from myst_parser.mdit_to_docutils.base import make_document
            from myst_parser.parsers.mdit import create_md_parser

            DocutilsParser = myst_parser.parsers.docutils_.Parser
            config: MdParserConfig = MdParserConfig(commonmark_only=False)
            md_parser = create_md_parser(config, DocutilsRenderer)

            doc = make_document(source_path=source_path, parser_cls=DocutilsParser)
            md_parser.options["document"] = doc
            md_parser.render(string)
        else:
            import docutils.utils
            from docutils.frontend import OptionParser
            from docutils.parsers.rst import Parser

            parser = Parser()
            settings = OptionParser(components=(Parser,)).get_default_values()

            doc = docutils.utils.new_document(
                source_path=str(source_path), settings=settings
            )
            parser.parse(string, doc)

        def condition(node: Node) -> bool:
            return (
                (
                    isinstance(node, (nodes.literal_block, nodes.comment))
                    and "testnodetype" in node
                )
                or (
                    isinstance(node, nodes.literal_block)
                    and re.match(
                        doctest.DocTestParser._EXAMPLE_RE, node.astext()  # type:ignore
                    )
                    is not None
                )
                or isinstance(node, nodes.doctest_block)
            )

        for idx, node in enumerate(doc.findall(condition)):
            logger.debug(f"() node: {node.astext()}")
            assert isinstance(node, nodes.Element)
            test_name = node.get("groups")
            if isinstance(test_name, list):
                test_name = test_name[0]
            if test_name is None or "default" == test_name:
                test_name = f"{name}[{idx}]"
            logger.debug(f"() node: {test_name}")
            test = self._get_test(
                string=node.astext(),
                name=test_name,
                filename=name,
                globs=globs,
                source_lines=[str(node.line)],
            )
            if test is not None:
                tests.append(test)

    def _get_test(
        self,
        string: str,
        name: str,
        filename: str,
        globs: t.Dict[str, t.Any],
        source_lines: t.List[str],
    ) -> doctest.DocTest:
        """
        Return a DocTest for the given string, if it defines a docstring;
        otherwise, return None.
        """
        lineno = int(source_lines[0])

        # Return a DocTest for this string.
        return self._parser.get_doctest(string, globs, name, filename, lineno)


def testdocutils(
    filename: str,
    module_relative: bool = True,
    name: t.Optional[str] = None,
    package: t.Optional[t.Union[str, types.ModuleType]] = None,
    globs: t.Optional[t.Dict[str, t.Any]] = None,
    verbose: t.Optional[bool] = None,
    report: bool = True,
    optionflags: int = 0,
    extraglobs: t.Optional[t.Dict[str, t.Any]] = None,
    raise_on_error: bool = False,
    parser: "doctest.DocTestParser" = parser,
    encoding: t.Optional[str] = None,
) -> doctest.TestResults:
    """Docutils-based test entrypoint.

    Based on doctest.testfile at python 3.10
    """
    global master

    if package and not module_relative:
        raise ValueError("Package may only be specified for module-" "relative paths.")

    # Keep the absolute file paths. This is needed for Include directies to work.
    # The absolute path will be applied to source_path when creating the docutils doc.
    text, _ = doctest._load_testfile(  # type: ignore
        filename, package, module_relative, encoding or "utf-8"
    )

    # If no name was given, then use the file's name.
    if name is None:
        name = os.path.basename(filename)

    # Assemble the globals.
    if globs is None:
        globs = {}
    else:
        globs = globs.copy()
    if extraglobs is not None:
        globs.update(extraglobs)
    if "__name__" not in globs:
        globs["__name__"] = "__main__"

    # Find, parse, and run all tests in the given module.
    finder = DocutilsDocTestFinder()

    runner: t.Union[doctest.DebugRunner, doctest.DocTestRunner]

    if raise_on_error:
        runner = doctest.DebugRunner(verbose=verbose, optionflags=optionflags)
    else:
        runner = doctest.DocTestRunner(verbose=verbose, optionflags=optionflags)

    for test in finder.find(text, filename, globs=globs, extraglobs=extraglobs):
        runner.run(test)

    if report:
        runner.summarize()

    if master is None:
        master = runner
    else:
        master.merge(runner)

    return doctest.TestResults(runner.failures, runner.tries)


def _test() -> int:
    """Changes from standard library at 3.10

    - Sets up logging.basicLogging(level=logging.DEBUG) w/ args.verbose
    """
    import argparse

    p = argparse.ArgumentParser(description="doctest runner")
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="logger.debug very verbose output for all tests",
    )
    p.add_argument(
        "--log-level",
        action="store",
        default=False,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )
    p.add_argument(
        "-o",
        "--option",
        action="append",
        choices=doctest.OPTIONFLAGS_BY_NAME.keys(),
        default=[],
        help=(
            "specify a doctest option flag to apply"
            " to the test run; may be specified more"
            " than once to apply multiple options"
        ),
    )
    p.add_argument(
        "-f",
        "--fail-fast",
        action="store_true",
        help=(
            "stop running tests after first failure (this"
            " is a shorthand for -o FAIL_FAST, and is"
            " in addition to any other -o options)"
        ),
    )
    p.add_argument(
        "--docutils",
        action="store_true",
        help=("Force parsing using docutils (reStructuredText, markdown)"),
    )
    p.add_argument("file", nargs="+", help="file containing the tests to run")
    args = p.parse_args()

    testfiles = args.file
    # Verbose used to be handled by the "inspect argv" magic in DocTestRunner,
    # but since we are using argparse we are passing it manually now.
    verbose = args.verbose
    if args.log_level:
        logging.basicConfig(level=args.log_level)
        # Quiet markdown-it
        md_logger = logging.getLogger("markdown_it.rules_block")
        md_logger.setLevel(logging.INFO)
    options = 0
    for option in args.option:
        options |= doctest.OPTIONFLAGS_BY_NAME[option]
    if args.fail_fast:
        options |= doctest.FAIL_FAST
    for filename in testfiles:
        if filename.endswith(".rst") or filename.endswith(".md") or args.docutils:
            failures, _ = testdocutils(
                filename,
                module_relative=False,
                verbose=verbose,
                optionflags=options,
            )
        elif filename.endswith(".py"):
            # It is a module -- insert its dir into sys.path and try to
            # import it. If it is part of a package, that possibly
            # won't work because of package imports.
            dirname, filename = os.path.split(filename)
            sys.path.insert(0, dirname)
            m = __import__(filename[:-3])
            del sys.path[0]
            failures, _ = doctest.testmod(m, verbose=verbose, optionflags=options)
        else:
            failures, _ = doctest.testfile(
                filename,
                module_relative=False,
                verbose=verbose,
                optionflags=options,
            )
        if failures:
            return 1
    return 0


if __name__ == "__main__":
    setup()
    sys.exit(_test())
