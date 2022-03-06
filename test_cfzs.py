import pytest

from cfzs import RR, diff

ex1 = RR('example.org', 3600, 'A', '192.0.2.1')
ex2 = RR('example.org', 3600, 'A', '192.0.2.2')
aex = RR('a.example.org', 3600, 'A', '192.0.2.1')
bex = RR('b.example.org', 3600, 'A', '192.0.2.1')


@pytest.mark.parametrize(('name', 'a', 'b', 'expected'), [
    ("replace ip", [ex1], [ex2], [(ex1, ex2)]),
    ("add first", [bex], [aex], [(None, aex), (bex, None)]),
    ("add last", [aex], [bex], [(aex, None), (None, bex)]),
])
def test_diff(name, a, b, expected):
    assert list(diff(a, b)) == expected
