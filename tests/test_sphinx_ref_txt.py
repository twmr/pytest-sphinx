import os


refname = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    'doctest.txt')


def test_collect_reftextfile(testdir):
    with open(refname) as fh:
        testdir.maketxtfile(test_ref=fh.read())

    result = testdir.runpytest('--doctest-modules')
    print(result.stdout.str())
    # for x in (testdir.tmpdir, ):
    #     items, reprec = testdir.inline_genitems(x)
    #     assert len(items) == 3
