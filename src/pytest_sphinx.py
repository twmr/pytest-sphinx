"""pytest_sphinx

pytest plugin for doctest w/ reStructuredText and markdown
"""
import bdb
import doctest
import logging
import sys
import types
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable
from typing import Optional
from typing import Tuple
from typing import Type

import _pytest
import pytest
from _pytest import outcomes
from _pytest.doctest import DoctestItem
from _pytest.outcomes import OutcomeException

from doctest_docutils import DocutilsDocTestFinder
from doctest_docutils import setup

if TYPE_CHECKING:
    import io
    from doctest import _Out

    _SpoofOut = io.StringIO

logger = logging.getLogger(__name__)

# Lazy definition of runner class
RUNNER_CLASS = None


def pytest_unconfigure() -> None:
    global RUNNER_CLASS

    RUNNER_CLASS = None


def pytest_collect_file(
    file_path: Path, parent: pytest.Collector
) -> Optional["SphinxDoctestFile"]:
    config = parent.config
    if _is_doctest(config, file_path, parent):
        return SphinxDoctestFile.from_parent(parent, path=file_path)  # type: ignore
    return None


def _is_doctest(config: pytest.Config, path: Path, parent: pytest.Collector) -> bool:
    if path.suffix in (".rst", ".md") and parent.session.isinitpath(path):
        return True
    globs = config.getoption("doctestglob") or ["*.rst", "*.md"]
    for glob in globs:
        if path.match(path_pattern=glob):
            return True
    return False


def _init_runner_class() -> Type["doctest.DocTestRunner"]:
    import doctest

    class PytestDoctestRunner(doctest.DebugRunner):
        """Runner to collect failures.

        Note that the out variable in this case is a list instead of a
        stdout-like object.
        """

        def __init__(
            self,
            checker: Optional["doctest.OutputChecker"] = None,
            verbose: Optional[bool] = None,
            optionflags: int = 0,
            continue_on_failure: bool = True,
        ) -> None:
            super().__init__(checker=checker, verbose=verbose, optionflags=optionflags)
            self.continue_on_failure = continue_on_failure

        def report_failure(
            self,
            out: "_Out",
            test: "doctest.DocTest",
            example: "doctest.Example",
            got: str,
        ) -> None:
            failure = doctest.DocTestFailure(test, example, got)
            if self.continue_on_failure:
                assert isinstance(out, list)
                out.append(failure)
            else:
                raise failure

        def report_unexpected_exception(
            self,
            out: "_Out",
            test: "doctest.DocTest",
            example: "doctest.Example",
            exc_info: Tuple[Type[BaseException], BaseException, types.TracebackType],
        ) -> None:
            if isinstance(exc_info[1], OutcomeException):
                raise exc_info[1]
            if isinstance(exc_info[1], bdb.BdbQuit):
                outcomes.exit("Quitting debugger")
            failure = doctest.UnexpectedException(test, example, exc_info)
            if self.continue_on_failure:
                assert isinstance(out, list)
                out.append(failure)
            else:
                raise failure

    return PytestDoctestRunner


def _get_runner(
    checker: Optional["doctest.OutputChecker"] = None,
    verbose: Optional[bool] = None,
    optionflags: int = 0,
    continue_on_failure: bool = True,
) -> "doctest.DocTestRunner":
    # We need this in order to do a lazy import on doctest
    global RUNNER_CLASS
    if RUNNER_CLASS is None:
        RUNNER_CLASS = _init_runner_class()
    # Type ignored because the continue_on_failure argument is only defined on
    # PytestDoctestRunner, which is lazily defined so can't be used as a type.
    return RUNNER_CLASS(  # type: ignore
        checker=checker,
        verbose=verbose,
        optionflags=optionflags,
        continue_on_failure=continue_on_failure,
    )


class SphinxDocTestRunner(doctest.DocTestRunner):
    def summarize(  # type: ignore
        self, out: "_Out", verbose: Optional[bool] = None
    ) -> Tuple[int, int]:
        string_io = StringIO()
        old_stdout = sys.stdout
        sys.stdout = string_io
        try:
            res = super().summarize(verbose)
        finally:
            sys.stdout = old_stdout
        out(string_io.getvalue())
        return res

    def _DocTestRunner__patched_linecache_getlines(
        self, filename: str, module_globals: Any = None
    ) -> Any:
        # this is overridden from DocTestRunner adding the try-except below
        m = self._DocTestRunner__LINECACHE_FILENAME_RE.match(filename)  # type: ignore
        if m and m.group("name") == self.test.name:
            try:
                example = self.test.examples[int(m.group("examplenum"))]
            # because we compile multiple doctest blocks with the same name
            # (viz. the group name) this might, for outer stack frames in a
            # traceback, get the wrong test which might not have enough examples
            except IndexError:
                pass
            else:
                return example.source.splitlines(True)
        return self.save_linecache_getlines(filename, module_globals)  # type: ignore


class SphinxDoctestFile(pytest.Module):
    def collect(self) -> Iterable[DoctestItem]:
        setup()

        encoding = self.config.getini("doctest_encoding")
        text = self.fspath.read_text(encoding)

        optionflags = _pytest.doctest.get_optionflags(self)  # type:ignore
        # Uses internal doctest module parsing mechanism.
        finder = DocutilsDocTestFinder()

        runner = _get_runner(
            verbose=False,
            optionflags=optionflags,
            checker=_pytest.doctest._get_checker(),
            continue_on_failure=_pytest.doctest._get_continue_on_failure(  # type:ignore
                self.config
            ),
        )

        for test in finder.find(
            text,
            str(self.fspath),
        ):
            if test.examples:  # skip empty doctests
                yield DoctestItem.from_parent(
                    self, name=test.name, runner=runner, dtest=test  # type: ignore
                )
