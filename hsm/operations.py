import functools
import heapq
import gettext

from hsm.toolkit import Arguments, Dataclass, Parameter, Coercion


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


class Operation(Dataclass):
    unique_name: str = Parameter(Coercion(None, str.upper, gettext.gettext), factory_key=True)
    symbol: str
    _: Parameter.KW_ONLY
    alternative_symbols: list[str] = Parameter(default_factory=list)
    n_args: int = 2
    commutative: bool = False
    comparison: bool = False
    swapped: str | None = None
    inverse: str | None = None
    chainable: bool = Parameter(
        default_factory=lambda self: self.n_args > 1,
        instance_factory=True
    )

    __call__ = staticmethod(OperationImplementation)

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return self(*item)
        return self(item)


class OpName:
    ADD = gettext.gettext('ADD')
    SUB = gettext.gettext('SUBTRACT')
    MUL = gettext.gettext('MULTIPLY')
    TRUEDIV = gettext.gettext('DIVIDE')
    FLOORDIV = gettext.gettext('FLOOR DIVIDE')
    MOD = gettext.gettext('REMAINDER')
    MATMUL = gettext.gettext('MATRIX MULTIPLY')
    POW = gettext.gettext('POWER')
    ROOT = gettext.gettext('ROOT')

    EQ = gettext.gettext('EQUAL')
    NE = gettext.gettext('NOT EQUAL')
    GE = gettext.gettext('GREATER OR EQUAL')
    GT = gettext.gettext('GREATER THAN')
    LE = gettext.gettext('LESS OR EQUAL')
    LT = gettext.gettext('LESS THAN')
    AND = gettext.gettext('AND')
    OR = gettext.gettext('OR')
    XOR = gettext.gettext('EXCLUSIVE OR')

    CONTAINS = gettext.gettext('CONTAINS')
    IS_IN = gettext.gettext('IS IN')
    GET = gettext.gettext('GET')

    ABS = gettext.gettext('ABSOLUTE')
    INVERT = gettext.gettext('INVERT')


class Ops:
    ADD = add = Operation(OpName.ADD, '+', commutative=True)
    SUB = sub = Operation(OpName.SUB, '-')
    MUL = mul = Operation(OpName.MUL, '*', commutative=True)
    TRUEDIV = truediv = Operation(OpName.TRUEDIV, '/')
    FLOORDIV = floordiv = Operation(OpName.FLOORDIV, '//')
    MOD = mod = Operation(OpName.MOD, '%')
    MATMUL = matmul = Operation(OpName.MATMUL, '@')
    POW = pow = Operation(OpName.POW, '**')
    ROOT = root = Operation(OpName.ROOT, '%(degree)r√%(self)r')

    EQ = eq = Operation(OpName.EQ, '==', commutative=True, comparison=True)
    NE = ne = Operation(OpName.NE, '!=', commutative=True, comparison=True)
    GE = ge = Operation(OpName.GE, '>=', swapped='LE', comparison=True)
    GT = gt = Operation(OpName.GT, '>', swapped='LT', comparison=True)
    LE = le = Operation(OpName.LE, '<=', swapped='GE', comparison=True)
    LT = lt = Operation(OpName.LT, '<', swapped='GT', comparison=True)

    AND = and_ = Operation(OpName.AND, '&', commutative=True)
    OR = or_ = Operation(OpName.OR, '|', commutative=True)
    XOR = xor_ = Operation(OpName.XOR, '^', commutative=True)

    CONTAINS = contains = Operation(OpName.CONTAINS, '∋', swapped='IS_IN')
    IS_IN = is_in = Operation(OpName.IS_IN, '∈', swapped='CONTAINS')
    GET = get = Operation(OpName.GET, '%(parent)r[%(self)r]')  # commutative only in the C language

    ABS = abs = Operation(OpName.ABS, '|%(self)r|', n_args=1)
    INVERT = invert = Operation(OpName.INVERT, '~%(self)r', n_args=1)
