import pytest

from zonesync.__init__ import RR, diff

ex1 = RR('example.org', 3600, 'A', '192.0.2.1')
ex2 = RR('example.org', 3600, 'A', '192.0.2.2')
aex = RR('a.example.org', 3600, 'A', '192.0.2.1')
bex = RR('b.example.org', 3600, 'A', '192.0.2.1')
cex = RR('c.example.org', 3600, 'A', '192.0.2.1')


@pytest.mark.parametrize(('name', 'a', 'b', 'expected'), [
    ("replace ip", {ex1}, {ex2}, {(ex1, ex2)}),
    ("add second ip", {ex1}, {ex1, ex2}, {(None, ex2)}),
    ("remove second ip", {ex1, ex2}, {ex1}, {(ex2, None)}),
    ("remove first ip", {ex1, ex2}, {ex2}, {(ex1, None)}),
    ("add first", {bex}, {aex}, {(bex, None), (None, aex)}),
    ("add last", {aex}, {bex}, {(aex, None), (None, bex)}),
    ("add middle", {aex, cex}, {aex, bex, cex}, {(None, bex)}),
])
def test_diff(name, a, b, expected):
    assert set(diff(a, b)) == expected
