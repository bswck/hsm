import functools
import heapq

from hsm._objects import Object, Parameter, factory


class Template(Object, factory_key='math_objects'):
    math_objects: tuple[int] = Parameter(kind=Parameter.VAR_POSITIONAL)

    def __post_init__(self):
        self.registry = []

    def __call__(self, algo=None, *, priority=None, cond=None):
        if algo is None:
            return functools.partial(self, priority=priority, cond=cond)
        heapq.heappush(self.registry, (priority, cond, algo))
        return algo


class Operation(Object, factory_key='unique_name'):
    unique_name: str
    symbol: str
    _: Parameter.KW_ONLY
    alternative_symbols: list[str] = factory(list)
    n_args: int = 2
    commutative: bool = False
    swapped: str | None = None
    inverse: str | None = None
    chainable: bool = factory(lambda self: self.n_args > 1, True)

    __getitem__ = __call__ = staticmethod(Template)


class Ops:
    ADD = add = Operation('ADD', '+', commutative=True)
    SUB = sub = Operation('SUB', '-')
    MUL = mul = Operation('MUL', '*', commutative=True)
    TRUEDIV = truediv = Operation('TRUEDIV', '/')
    FLOORDIV = floordiv = Operation('FLOORDIV', '//')
    MOD = mod = Operation('MOD', '%')
    MATMUL = matmul = Operation('MATMUL', '@')
    POW = pow = Operation('POW', '**')
    ROOT = root = Operation('ROOT', '√')

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
    GET = getitem = Operation('GET', '[]')  # commutative, but only in the C language

    ABS = abs = Operation('ABS', 'abs', n_args=1)
    INVERT = invert = Operation('INVERT', '~', n_args=1)

    IADD = iadd = Operation('IADD', '+=')
    IAND = iand = Operation('IAND', '&=')
    ICONCAT = iconcat = Operation('ICONCAT', '+=')
    IFLOORDIV = ifloordiv = Operation('IFLOORDIV', '//=')
    IMATMUL = imatmul = Operation('IMATMUL', '@=')
    IMOD = imod = Operation('IMOD', '%=')
    IMUL = imul = Operation('IMUL', '*=')
    IOR = ior = Operation('IOR', '|=')
    IPOW = ipow = Operation('IPOW', '**=')
    ISUB = isub = Operation('ISUB', '-=')
    ITRUEDIV = itruediv = Operation('ITRUEDIV', '/=')
