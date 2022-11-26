import functools
import heapq
from typing import Optional, Callable

from hsm.toolkit import Arguments, Dataclass, Parameter, Coercion, Argument, Namespace
from hsm.toolkit import coercion_factory


@functools.singledispatch
def as_object(value):
    raise ValueError(f'value {value!r} could not be recognised as a mathematical object')


class Context(Namespace):
    pass


@coercion_factory(lambda tp: Coercion(tp, cast=as_object))
class Object:
    const = False

    def _get_value(self, context):
        raise NotImplementedError

    def get_value(self, context=None):
        return self._get_value(context or Context())

    def __add__(self, other):
        return Operation('add', self, other)

    add = __add__

    def __sub__(self, other):
        return Operation('sub', self, other)

    sub = __sub__

    def __mul__(self, other):
        return Operation('mul', self, other)

    mul = __mul__

    def __truediv__(self, other):
        return Operation('div', self, other)

    div = __truediv__

    def __floordiv__(self, other):
        return Operation('floordiv', self, other)

    floordiv = __floordiv__

    def __mod__(self, other):
        return Operation('mod', self, other)

    mod = __mod__

    def __matmul__(self, other):
        return Operation('matmul', self, other)

    matmul = __matmul__

    def __pow__(self, other):
        return Operation('pow', self, other)

    pow = __pow__

    def root(self, other):
        return Operation('root', self, other)

    def __eq__(self, other):
        return Operation('eq', self, other)

    eq = __eq__

    def __ne__(self, other):
        return Operation('ne', self, other)

    ne = __ne__

    def __ge__(self, other):
        return Operation('ge', self, other)

    ge = __ge__

    def __gt__(self, other):
        return Operation('gt', self, other)

    gt = __gt__

    def __le__(self, other):
        return Operation('le', self, other)

    le = __le__

    def __lt__(self, other):
        return Operation('lt', self, other)

    lt = __lt__

    def __and__(self, other):
        return Operation('and', self, other)

    and_ = __and__

    def __or__(self, other):
        return Operation('or', self, other)

    or_ = __or__

    def __xor__(self, other):
        return Operation('xor', self, other)

    xor = __xor__

    def __contains__(self, other):
        return Operation('contains', self, other)

    contains = __contains__

    def in_(self, other):
        return Operation('in', self, other)

    def __get__(self, other):
        return Operation('get', self, other)

    get = __get__

    def abs(self):
        return Operation('abs', self)

    def __invert__(self, other):
        return Operation('invert', self)

    invert = __invert__


class OperationRegistry(dict):
    def push(self, *operand_types, impl, symmetrical=True):
        if symmetrical:
            self[frozenset(operand_types)] = impl
        else:
            self[operand_types] = impl

    def get(self, *operand_types):
        try:
            return self[frozenset(operand_types)]
        except KeyError:
            try:
                return self[operand_types]
            except KeyError as exc:
                raise exc from None


operations = OperationRegistry()


class OperationImplementation(Dataclass):
    operand_types: tuple[type, ...] = Arguments(
        factory_key=True,
        cast=False,
    )
    registry: OperationRegistry = Parameter(default_factory=lambda: operations)

    def __post_init__(self):
        self.dispatch = []
        self.registry.push(self.operand_types, impl=self)

    def __call__(self, fn=None, *, priority=0, cond=None):
        if fn is None:
            return functools.partial(self, priority=priority, cond=cond)
        heapq.heappush(self.dispatch, (-priority, cond, fn))
        return fn


class OperationKind(Dataclass):
    name: str = Parameter(Coercion(None, str.upper), factory_key=True)
    repr: str
    _: Parameter.KW_ONLY
    symbols: list[str] = Parameter(default_factory=list)
    nargs: int = 2
    commutative: bool = False
    comparison: bool = False
    swapped: str | None = None
    inverse: str | None = None
    chainable: bool = Parameter(
        default_factory=lambda self: self.nargs > 1,
        instance_factory=True
    )

    __call__ = staticmethod(OperationImplementation)

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return self(*item)
        return self(item)


class Op:
    ADD = 'add'
    SUB = 'sub'
    MUL = 'mul'
    DIV = 'div'
    FLOORDIV = 'floordiv'
    MOD = 'mod'
    MATMUL = 'matmul'
    POW = 'pow'
    ROOT = 'root'

    EQ = 'eq'
    NE = 'ne'
    GE = 'ge'
    GT = 'gt'
    LE = 'le'
    LT = 'lt'

    AND = 'and'
    OR = 'or'
    XOR = 'xor'

    CONTAINS = 'contains'
    IN = 'in'
    GET = 'get'

    ABS = 'abs'
    INVERT = 'invert'


class Operations:
    ADD = add = OperationKind(Op.ADD, '{0} + {1}', commutative=True)
    SUB = sub = OperationKind(Op.SUB, '{0} - {1}')
    MUL = mul = OperationKind(Op.MUL, '{0} * {1}', commutative=True)
    DIV = div = OperationKind(Op.DIV, '{0} / {1}')
    FLOORDIV = floordiv = OperationKind(Op.FLOORDIV, '{0} // {1}')
    MOD = mod = OperationKind(Op.MOD, '{0} % {1}')
    MATMUL = matmul = OperationKind(Op.MATMUL, '{0} @ {1}')
    POW = pow = OperationKind(Op.POW, '{0} ** {1}')
    ROOT = root = OperationKind(Op.ROOT, '{0}^(1/{1})')

    EQ = eq = OperationKind(
        Op.EQ, '{0} == {1}', commutative=True, comparison=True
    )
    NE = ne = OperationKind(
        Op.NE, '{0} != {1}', commutative=True, comparison=True
    )
    GE = ge = OperationKind(
        Op.GE, '{0} >= {1}', swapped='LE', comparison=True
    )
    GT = gt = OperationKind(
        Op.GT, '{0} > {1}', swapped='LT', comparison=True
    )
    LE = le = OperationKind(
        Op.LE, '{0} <= {1}', swapped='GE', comparison=True
    )
    LT = lt = OperationKind(
        Op.LT, '{0} < {1}', swapped='GT', comparison=True
    )

    AND = and_ = OperationKind(Op.AND, '{0} & {1}', commutative=True)
    OR = or_ = OperationKind(Op.OR, '{0} | {1}', commutative=True)
    XOR = xor_ = OperationKind(Op.XOR, '{0} ^ {1}', commutative=True)

    CONTAINS = contains = OperationKind(
        Op.CONTAINS, '{1} ∈ {0}', swapped='IS_IN'
    )
    IN = in_ = OperationKind(Op.IN, '{0} ∈ {1}', swapped='CONTAINS')
    GET = get = OperationKind(Op.GET, '{1}[{0}]')

    ABS = abs = OperationKind(Op.ABS, '|{0}|', nargs=1)
    INVERT = invert = OperationKind(Op.INVERT, '~{0}', nargs=1)


class Operation(Dataclass):
    """
    Operation on objects.

    Operation('lt', x, y, 5) -> x < y < 5
    Operation('abs', 5) -> |5|
    Operation('abs', x) -> |x|
    Operation('abs', x, 5) -> ValueError: ...
    """

    kind: OperationKind
    objects: list[Object] = Arguments()

    chained = False

    def _get_value(self, context):
        return

    def __post_init__(self):
        if self.kind.nargs != -1:
            nargs = len(self)
            if nargs < self.kind.nargs:
                raise ValueError(
                    f'incorrect number of arguments for the {self.kind.name} operation '
                    f'(expected {self.kind.nargs}, got {nargs})'
                )
            if nargs > self.kind.nargs:
                if not self.kind.chainable:
                    raise ValueError(
                        f'{self.kind.name} operation is not chainable '
                        '(too many arguments passed)'
                    )
                self.chained = True

    def __repr__(self):
        repr_string = self.kind.repr.format(*self.objects)
        if self.chained:
            repr_string = functools.reduce(
                self.kind.repr.format,
                self.objects[self.kind.nargs::],
                repr_string
            )
        return repr_string

    def __len__(self):
        return len(self.objects)


@as_object.register(Object)
def identity(obj):
    return obj


class Symbol(Dataclass):
    name: str = Parameter(default='x', factory_key=True)

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
    impl = Parameter(default=None)  # type: Optional[Callable]
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
