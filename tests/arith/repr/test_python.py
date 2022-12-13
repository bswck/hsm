from hsm.arith.tree import x, y, z


def test_associativity():
    assert repr(x + y + z) == 'x + y + z'
    assert repr((x + y) + z) == 'x + y + z'
    assert repr(x + (y + z)) == 'x + y + z'
    assert repr((x + y) - z) == 'x + y - z'
    assert repr(x + (y - z)) == 'x + y - z'
    assert repr(x - (y - z)) == 'x - (y - z)'
    assert repr(x - y - z) == 'x - y - z'
    assert repr(x / y / z) == 'x / y / z'
    assert repr((x / y) / z) == 'x / y / z'
    assert repr(x / (y / z) / x) == 'x / (y / z) / x'
    assert repr(x / (y / z / x)) == 'x / (y / z / x)'
    assert repr(x - y / (y / z) + z) == 'x - y / (y / z) + z'


def test_negative():
    assert repr(-x) == '-x'
    assert repr(-(-x)) == 'x'
    assert repr(-(-x ** 2 + 2*x - 3)) == '-(-(x^2) + 2 * x - 3)'
    assert repr(-((-x) ** 2 + 2*x - 3)) == '-((-x)^2 + 2 * x - 3)'
    assert repr(-(x + y)) == '-(x + y)'
    assert repr(x + y + -1) == 'x + y + (-1)'
    assert repr(-1 + x + y) == '-1 + x + y'


def test_priority():
    assert repr(-1 * x + y) == '-1 * x + y'
    assert repr(-1 * (x + y)) == '-1 * (x + y)'
    assert repr(-1 + (x * y)) == '-1 + x * y'
