import functools
import heapq

from hsm.object import Object
from hsm.toolkit import Arguments, Dataclass, Parameter, Coercion, Argument


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
    ADD = add = OperationKind(Op.ADD, '{0!r} + {1!r}', commutative=True)
    SUB = sub = OperationKind(Op.SUB, '{0!r} - {1!r}')
    MUL = mul = OperationKind(Op.MUL, '{0!r} * {1!r}', commutative=True)
    DIV = div = OperationKind(Op.DIV, '{0!r} / {1!r}')
    FLOORDIV = floordiv = OperationKind(Op.FLOORDIV, '{0!r} // {1!r}')
    MOD = mod = OperationKind(Op.MOD, '{0!r} % {1!r}')
    MATMUL = matmul = OperationKind(Op.MATMUL, '{0!r} @ {1!r}')
    POW = pow = OperationKind(Op.POW, '{0!r} ** {1!r}')
    ROOT = root = OperationKind(Op.ROOT, '%(degree)r√{0!r}')

    EQ = eq = OperationKind(
        Op.EQ, '{0!r} == {1!r}', commutative=True, comparison=True
    )
    NE = ne = OperationKind(
        Op.NE, '{0!r} != {1!r}', commutative=True, comparison=True
    )
    GE = ge = OperationKind(
        Op.GE, '{0!r} >= {1!r}', swapped='LE', comparison=True
    )
    GT = gt = OperationKind(
        Op.GT, '{0!r} > {1!r}', swapped='LT', comparison=True
    )
    LE = le = OperationKind(
        Op.LE, '{0!r} <= {1!r}', swapped='GE', comparison=True
    )
    LT = lt = OperationKind(
        Op.LT, '{0!r} < {1!r}', swapped='GT', comparison=True
    )

    AND = and_ = OperationKind(Op.AND, '{0!r} & {1!r}', commutative=True)
    OR = or_ = OperationKind(Op.OR, '{0!r} | {1!r}', commutative=True)
    XOR = xor_ = OperationKind(Op.XOR, '{0!r} ^ {1!r}', commutative=True)

    CONTAINS = contains = OperationKind(
        Op.CONTAINS, '{1!r} ∈ {0!r}', swapped='IS_IN'
    )
    IN = in_ = OperationKind(Op.IN, '{0!r} ∈ {1!r}', swapped='CONTAINS')
    GET = get = OperationKind(Op.GET, '{1!r}[{0!r}]')

    ABS = abs = OperationKind(Op.ABS, '|{0!r}|', nargs=1)
    INVERT = invert = OperationKind(Op.INVERT, '~{0!r}', nargs=1)


class Operation(Dataclass):
    """
    Operation on objects.

    Operation('lt', x, y, 5) -> x < y < 5
    Operation('abs', 5) -> |5|
    Operation('abs', x) -> |x|
    Operation('abs', x, 5) -> ValueError: ...
    """

    kind: OperationKind = Argument()
    objects: list[Object] = Arguments()

    def __post_init__(self):
        if self.kind.nargs != -1:
            nargs = len(self)
            if nargs < self.kind.nargs:
                raise ValueError(
                    f'incorrect number of arguments for the {self.kind.name} operation '
                    f'(expected {self.kind.nargs}, got {nargs})'
                )
            if nargs > self.kind.nargs and not self.kind.chainable:
                raise ValueError(f'{self.kind.name} operation is not chainable')

    def __repr__(self):
        return self.kind.repr.format(*self.objects)

    def __len__(self):
        return len(self.objects)


print(Operation('lt', 5, 3))
