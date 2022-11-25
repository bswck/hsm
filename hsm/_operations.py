import functools
import heapq

from hsm._autoclasses import AutoClass, Parameter


class GlobalOperationRegistry(dict):
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


class OperationImplementation(AutoClass):
    operand_types: tuple[type, ...] = Parameter(
        factory_key=True,
        kind=Parameter.VAR_POSITIONAL,
        cast=False,
    )
    registry: GlobalOperationRegistry = Parameter(default_factory=GlobalOperationRegistry)

    def __post_init__(self):
        self.dispatch = []
        self.registry.push(self.operand_types, impl=self)

    def __call__(self, fn=None, *, priority=0, cond=None):
        if fn is None:
            return functools.partial(self, priority=priority, cond=cond)
        heapq.heappush(self.dispatch, (-priority, cond, fn))
        return fn


class Operation(AutoClass):
    unique_name: str = Parameter(factory_key=True)
    symbol: str
    _: Parameter.KW_ONLY
    alternative_symbols: list[str] = Parameter(default_factory=list)
    n_args: int = 2
    commutative: bool = False
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


class Ops:
    ADD = add = Operation('ADD', '+', commutative=True)
    SUB = sub = Operation('SUB', '-')
    MUL = mul = Operation('MUL', '*', commutative=True)
    TRUEDIV = truediv = Operation('TRUEDIV', '/')
    FLOORDIV = floordiv = Operation('FLOORDIV', '//')
    MOD = mod = Operation('MOD', '%')
    MATMUL = matmul = Operation('MATMUL', '@')
    POW = pow = Operation('POW', '**')
    ROOT = root = Operation('ROOT', '%(degree)r√%(self)r')

    EQ = eq = Operation('EQ', '==', commutative=True)
    NE = ne = Operation('NE', '!=', commutative=True)
    GE = ge = Operation('GE', '>=', swapped='LE')
    GT = gt = Operation('GT', '>', swapped='LT')
    LE = le = Operation('LE', '<=', swapped='GE')
    LT = lt = Operation('LT', '<', swapped='GT')

    AND = and_ = Operation('AND', '&', commutative=True)
    OR = or_ = Operation('OR', '|', commutative=True)
    XOR = xor_ = Operation('XOR', '^', commutative=True)

    CONTAINS = contains = Operation('CONTAINS', '∋', swapped='IS_IN')
    IS_IN = is_in = Operation('IS_IN', '∈', swapped='CONTAINS')
    GET = get = Operation('GET', '%(parent)r[%(self)r]')  # commutative, but only in the C language

    ABS = abs = Operation('ABS', '|%(self)r|', n_args=1)
    INVERT = invert = Operation('INVERT', '~%(self)r', n_args=1)

    # IADD = iadd = Operation('IADD', '+=')
    # IAND = iand = Operation('IAND', '&=')
    # ICONCAT = iconcat = Operation('ICONCAT', '+=')
    # IFLOORDIV = ifloordiv = Operation('IFLOORDIV', '//=')
    # IMATMUL = imatmul = Operation('IMATMUL', '@=')
    # IMOD = imod = Operation('IMOD', '%=')
    # IMUL = imul = Operation('IMUL', '*=')
    # IOR = ior = Operation('IOR', '|=')
    # IPOW = ipow = Operation('IPOW', '**=')
    # ISUB = isub = Operation('ISUB', '-=')
    # ITRUEDIV = itruediv = Operation('ITRUEDIV', '/=')
