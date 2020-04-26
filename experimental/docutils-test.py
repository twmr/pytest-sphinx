import doctest
import logging
import pprint
import re
import sys
from os import path

import docutils.frontend
import docutils.nodes
import docutils.parsers.rst
import docutils.utils
import pytest_sphinx
from docutils import nodes
from docutils.parsers.rst import directives

logger = logging.getLogger(__name__)


blankline_re = re.compile(r"^\s*<BLANKLINE>", re.MULTILINE)
doctestopt_re = re.compile(r"#\s*doctest:.+$", re.MULTILINE)


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

        # self.set_source_info(node)
        # if test is not None:
        #     # only save if it differs from code
        #     node['test'] = test
        # if self.name == 'doctest':
        #     # if self.config.highlight_language in ('py', 'python'):
        #     #     node['language'] = 'pycon'
        #     # else:
        #     #     node['language'] = 'pycon3'  # default
        # elif self.name == 'testcode':
        #     if self.config.highlight_language in ('py', 'python'):
        #         node['language'] = 'python'
        #     else:
        #         node['language'] = 'python3'  # default
        # elif self.name == 'testoutput':
        #     # don't try to highlight output
        #     node['language'] = 'none'
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
                        __("missing '+' or '-' in '%s' option.") % option,
                        line=self.lineno,
                    )
                    continue
                if option_name not in doctest.OPTIONFLAGS_BY_NAME:
                    self.state.document.reporter.warning(
                        __("'%s' is not a valid option.") % option_name,
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
    # TODO:  Work out how to store or calculate real (file-relative)
    #       line numbers for doctest blocks in docstrings.
    if ":docstring of " in path.basename(node.source or ""):
        # The line number is given relative to the stripped docstring,
        # not the file.  This is correct where it is set, in
        # `docutils.nodes.Node.setup_child`, but Sphinx should report
        # relative to the file, not the docstring.
        return None
    if node.line is not None:
        # TODO: find the root cause of this off by one error.
        return node.line - 1
    return None


def get_sections(docstring):
    # doctree = parse_rst(open('demo.rst').read())
    # doctree = parse_rst(open('doctest.txt').read())
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
        node_options = node.get("options")
        node_groups = node.get("groups", ["default"])
        line_number = get_line_number(node)
        print(
            f"Node: {node_type} {node_options} {node_groups} {line_number} "
            f": {source}"
        )
        # if not source:
        #     logger.warning('no code/output in %s block',
        #                    node_type)
        # code = TestCode(source, type=node_type,
        #                 filename=filename, lineno=line_number,
        #                 options=node_options)
        # import pdb; pdb.set_trace()
        sections.append(
            pytest_sphinx.Section(
                node_type,
                source,
                node.get("skipif"),
                node_options,
                line_number,
                node_groups,
            )
        )

    print(sections)
    return sections


# sections = get_sections(open("doctest.txt").read())
sections = get_sections(open("using_the_shapereader.rst").read())
print([s.lineno for s in sections])
