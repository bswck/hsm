import functools

from hsm.functional.protocol import Protocol
from hsm.toolkit import Dataclass, Argument, Arguments, Parameter, Coercion, coercion_factory


# Forward declaration for BasicExpression class
def _operation(*args, **kwargs) -> 'Operation':
    return Operation(*args, **kwargs)


@coercion_factory(lambda tp: Coercion(tp, cast=hsm_object))
class AtomicNode:
    operation = _operation
    const = False

    def _get_value(self, context):
        raise NotImplementedError

    def get_value(self, context=None):
        return self._get_value(context or {})

    def __add__(self, other):
        return self.operation('add', self, other)

    def __radd__(self, other):
        return self.operation('add', other, self)

    add = __add__

    def __sub__(self, other):
        return self.operation('sub', self, other)

    def __rsub__(self, other):
        return self.operation('sub', other, self)

    sub = __sub__

    def __mul__(self, other):
        return self.operation('mul', self, other)

    def __rmul__(self, other):
        return self.operation('mul', other, self)

    mul = __mul__

    def __truediv__(self, other):
        return self.operation('div', self, other)

    def __rtruediv__(self, other):
        return self.operation('div', other, self)

    div = __truediv__

    def __floordiv__(self, other):
        return self.operation('floordiv', self, other)

    def __rfloordiv__(self, other):
        return self.operation('floordiv', other, self)

    floordiv = __floordiv__

    def __mod__(self, other):
        return self.operation('mod', self, other)

    def __rmod__(self, other):
        return self.operation('mod', other, self)

    mod = __mod__

    def __matmul__(self, other):
        return self.operation('matmul', self, other)

    def __rmatmul__(self, other):
        return self.operation('matmul', other, self)

    matmul = __matmul__

    def __pow__(self, other):
        return self.operation('pow', self, other)

    def __rpow__(self, other):
        return self.operation('pow', other, self)

    pow = __pow__

    def root(self, other):
        return self.operation('root', self, other)

    def __eq__(self, other):
        return self.operation('eq', self, other)

    eq = __eq__

    def __ne__(self, other):
        return self.operation('ne', self, other)

    ne = __ne__

    def __ge__(self, other):
        return self.operation('ge', self, other)

    ge = __ge__

    def __gt__(self, other):
        return self.operation('gt', self, other)

    gt = __gt__

    def __le__(self, other):
        return self.operation('le', self, other)

    le = __le__

    def __lt__(self, other):
        return self.operation('lt', self, other)

    lt = __lt__

    def __and__(self, other):
        return self.operation('and', self, other)

    def __rand__(self, other):
        return self.operation('and', other, self)

    and_ = __and__

    def __or__(self, other):
        return self.operation('or', self, other)

    def __ror__(self, other):
        return self.operation('or', other, self)

    or_ = __or__

    def __xor__(self, other):
        return self.operation('xor', self, other)

    def __rxor__(self, other):
        return self.operation('xor', other, self)

    xor = __xor__

    def contains(self, other):
        return self.operation('contains', self, other)

    def in_(self, other):
        return self.operation('contains', other, self)

    def __getitem__(self, other):
        return self.operation('get', self, other)

    get = __getitem__

    def abs(self):
        return self.operation('abs', self)

    def __invert__(self, other):
        return self.operation('invert', self)

    invert = __invert__


class Symbol(Dataclass, AtomicNode):
    name: str = Parameter(default='x', factory_key=True)

    def _get_value(self, context):
        return context[self.name]

    def __repr__(self):
        return self.name


def symbols(name_string):
    if name_string.isalpha():
        names = name_string
    else:
        names = name_string.replace(' ', ',').split(',')
    return tuple(map(Symbol, names))


_ = 'abcdefghijklmnopqrstuvwxyz'
a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z = symbols(_)


class Constraint(Dataclass):
    impl = Parameter(default=None)
    description: str | None = Parameter(
        Coercion(None, str.strip),
        default_factory=lambda self: str(self.impl) if isinstance(self.impl, Definition) else None,
        instance_factory=True
    )

    def check(self, context):
        if callable(self.impl) and not self.impl(context):
            description = ': ' + self.description if self.description else ''
            raise ValueError(f'constraint failed for {context}{description}')


class Definition(Dataclass):
    constraint: Constraint
    constraints: tuple[Constraint, ...] = Arguments()


@functools.singledispatch
def hsm_object(value):
    raise ValueError(f'value {value!r} could not be recognised as an HSM object')


@hsm_object.register(AtomicNode)
def identity(obj):
    return obj


class Function(Dataclass):
    objects: tuple[AtomicNode, ...] = Arguments(factory_key=True)

    chained_arguments = False
    _const = False

    @property
    def const(self):
        return self._const

    def __post_init__(self):
        if all(obj.const for obj in self.objects):
            self._const = True


class Operation(Function):
    """
    Single operation on certain objects.
    Chainable depending on the operation kind.

    Operation('lt', x, y, 5) -> x < y < 5
    Operation('abs', 5) -> |5|
    Operation('abs', x) -> |x|
    Operation('abs', x, 5) -> ValueError: ...not chainable...
    """
    protocol: Protocol = Argument(factory_key=True)

    def __post_init__(self):
        self.protocol.validate_args(self, self.objects)
        super().__post_init__()

    def commutate(self):
        pass

    def sort(self):
        pass

    def shorten(self):
        pass

    def convert(self, protocol):
        pass

    def merge(self, operation):
        pass

    def repr(self):
        return self.protocol.repr(self, self.objects)

    if __debug__:
        def __repr__(self):
            return self.repr()
