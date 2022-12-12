from hsm.arith.tree import x, y, z


def test_python_engine():
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
