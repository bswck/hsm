import pytest

from hsm.ops import op


@pytest.fixture
def x():
    return op('x')


@pytest.fixture
def y():
    return op('y')


@pytest.fixture
def z():
    return op('z')
