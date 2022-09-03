# doctest w/ myst-parser examples

## Barebones `doctest_block`

Welcome, here's my first thing:

```
>>> 2 + 2
4
>>> continents = 7
>>> print(f'hello world, there are {continents} continents')
hello world, there are 7 continents
```

## sphinx.ext.doctest-like directives (basic)

Another:

```{doctest} My example
>>> 2 + 3
5
```

```{doctest} A second
>>> 1 + 8
9
>>> 2 - 8
-6
```
