import functools
import heapq
import operator
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

    def __radd__(self, other):
        return Operation('add', other, self)

    add = __add__

    def __sub__(self, other):
        return Operation('sub', self, other)

    def __rsub__(self, other):
        return Operation('rsub', other, self)

    sub = __sub__

    def __mul__(self, other):
        return Operation('mul', self, other)

    def __rmul__(self, other):
        return Operation('mul', other, self)

    mul = __mul__

    def __truediv__(self, other):
        return Operation('div', self, other)

    def __rtruediv__(self, other):
        return Operation('div', other, self)

    div = __truediv__

    def __floordiv__(self, other):
        return Operation('floordiv', self, other)

    def __rfloordiv__(self, other):
        return Operation('floordiv', other, self)

    floordiv = __floordiv__

    def __mod__(self, other):
        return Operation('mod', self, other)

    def __rmod__(self, other):
        return Operation('mod', other, self)

    mod = __mod__

    def __matmul__(self, other):
        return Operation('matmul', self, other)

    def __rmatmul__(self, other):
        return Operation('matmul', other, self)

    matmul = __matmul__

    def __pow__(self, other):
        return Operation('pow', self, other)

    def __rpow__(self, other):
        return Operation('pow', other, self)

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

    def __rand__(self, other):
        return Operation('and', other, self)

    and_ = __and__

    def __or__(self, other):
        return Operation('or', self, other)

    def __ror__(self, other):
        return Operation('or', other, self)

    or_ = __or__

    def __xor__(self, other):
        return Operation('xor', self, other)

    def __rxor__(self, other):
        return Operation('xor', other, self)

    xor = __xor__

    def contains(self, other):
        return Operation('contains', self, other)

    def in_(self, other):
        return Operation('contains', other, self)

    def __getitem__(self, other):
        return Operation('get', self, other)

    get = __getitem__

    def abs(self):
        return Operation('abs', self)

    def __invert__(self, other):
        return Operation('invert', self)

    invert = __invert__


class PatternRegistry(dict):
    def push(self, *arguments, impl, symmetrical=True):
        if symmetrical:
            self[frozenset(arguments)] = impl
        else:
            self[arguments] = impl

    def fetch(self, *arguments):
        try:
            return self[frozenset(arguments)]
        except KeyError:
            try:
                return self[arguments]
            except KeyError as exc:
                raise exc from None


operations = PatternRegistry()


class OperationImplementation(Dataclass):
    operand_types: tuple[type, ...] = Arguments(
        factory_key=True,
        cast=False,
    )
    registry: PatternRegistry = Parameter(default_factory=lambda: operations)

    def __post_init__(self):
        self.dispatch = []
        self.registry.push(self.operand_types, impl=self)

    def __call__(self, fn=None, *, priority=0, cond=None):
        if fn is None:
            return functools.partial(self, priority=priority, cond=cond)
        heapq.heappush(self.dispatch, (-priority, cond, fn))
        return fn


class OpKind(Dataclass):
    name: str = Parameter(Coercion(None, str.upper), factory_key=True)
    repr: str
    _: Parameter.KW_ONLY
    symbols: list[str] = Parameter(default_factory=list)
    nargs: int = 2
    commutative: bool = False
    comparison: bool = False
    swapped_opkind: str | None = None
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


_OP_NAMES = set()


def _op_name(name):
    _OP_NAMES.add(name)
    return name


class Op:
    ADD = _op_name('add')
    SUB = _op_name('sub')
    MUL = _op_name('mul')
    DIV = _op_name('div')
    FLOORDIV = _op_name('floordiv')
    MOD = _op_name('mod')
    MATMUL = _op_name('matmul')
    POW = _op_name('pow')
    ROOT = _op_name('root')
    EQ = _op_name('eq')
    NE = _op_name('ne')
    GE = _op_name('ge')
    GT = _op_name('gt')
    LE = _op_name('le')
    LT = _op_name('lt')
    AND = _op_name('and')
    OR = _op_name('or')
    XOR = _op_name('xor')
    CONTAINS = _op_name('contains')
    IN = _op_name('in')
    GET = _op_name('get')
    ABS = _op_name('abs')
    INVERT = _op_name('invert')

    ALL = _OP_NAMES

    @classmethod
    def is_name(cls, name):
        return name in cls.ALL


del _OP_NAMES, _op_name


class Operations:
    ADD = add = OpKind(Op.ADD, '{0} + {1}', commutative=True)
    SUB = sub = OpKind(Op.SUB, '{0} - {1}')
    MUL = mul = OpKind(Op.MUL, '{0} * {1}', commutative=True)
    DIV = div = OpKind(Op.DIV, '{0} / {1}')
    FLOORDIV = floordiv = OpKind(Op.FLOORDIV, '{0} // {1}')
    MOD = mod = OpKind(Op.MOD, '{0} % {1}')
    MATMUL = matmul = OpKind(Op.MATMUL, '{0} @ {1}')
    POW = pow = OpKind(Op.POW, '{0} ** {1}')
    ROOT = root = OpKind(Op.ROOT, '{0}^(1/{1})')

    EQ = eq = OpKind(Op.EQ, '{0} == {1}', commutative=True, comparison=True)
    NE = ne = OpKind(Op.NE, '{0} != {1}', commutative=True, comparison=True)
    GE = ge = OpKind(Op.GE, '{0} >= {1}', swapped_opkind=Op.LE, comparison=True)
    GT = gt = OpKind(Op.GT, '{0} > {1}', swapped_opkind=Op.LT, comparison=True)
    LE = le = OpKind(Op.LE, '{0} <= {1}', swapped_opkind=Op.GE, comparison=True)
    LT = lt = OpKind(Op.LT, '{0} < {1}', swapped_opkind=Op.GT, comparison=True)

    AND = and_ = OpKind(Op.AND, '{0} & {1}', commutative=True)
    OR = or_ = OpKind(Op.OR, '{0} | {1}', commutative=True)
    XOR = xor_ = OpKind(Op.XOR, '{0} ^ {1}', commutative=True)

    CONTAINS = contains = OpKind(Op.CONTAINS, '{1} ∈ {0}')
    GET = get = OpKind(Op.GET, '{1}[{0}]')

    ABS = abs = OpKind(Op.ABS, '|{0}|', nargs=1)
    INVERT = invert = OpKind(Op.INVERT, '~{0}', nargs=1)


class OpConversion(Dataclass):
    orig_opkind: OpKind = Argument(factory_key=True)
    opkind: OpKind = Argument(factory_key=True)
    symmetrical: bool = True

    def as_key(self):
        if self.symmetrical:
            return frozenset((self.orig_opkind.name, self.opkind.name))
        return self.orig_opkind, self.opkind


def inverse(operand):
    return 1 / operand


default_conversions = PatternRegistry([
    (OpConversion('add', 'sub').as_key(), operator.neg),
    (OpConversion('mul', 'div').as_key(), inverse),
    (OpConversion('pow', 'root').as_key(), inverse)
])


class Operation(Dataclass):
    """
    Operation on objects.
    Chainable depending on the operation kind.

    Operation('lt', x, y, 5) -> x < y < 5
    Operation('abs', 5) -> |5|
    Operation('abs', x) -> |x|
    Operation('abs', x, 5) -> ValueError: ...
    """

    opkind: OpKind = Argument(factory_key=True)
    objects: tuple[Object, ...] = Arguments(factory_key=True)

    chained = False
    conversions = default_conversions

    def _get_value(self, context):
        return

    def __post_init__(self):
        if self.opkind.nargs != -1:
            nargs = len(self)
            if nargs < self.opkind.nargs:
                raise ValueError(
                    f'too few arguments for {self.opkind.name} '
                    f'(expected {self.opkind.nargs}, got {nargs})'
                )
            if nargs > self.opkind.nargs:
                if not self.opkind.chainable:
                    raise ValueError(
                        f'{self.opkind.name} operation is not chainable '
                        '(too many arguments passed)'
                    )
                self.chained = True

    def reassemble(self, reassembler='generic', fn=None, strict=False):
        opkind = ret = None
        reassembler = reassembler.casefold()

        if reassembler in {'generic', 'swap', 'commutate'}:
            if reassembler != 'commutate':
                if not self.opkind.swapped_opkind:
                    if strict and reassembler != 'generic':
                        raise ValueError(f'{self.opkind.name} operation is unswappable')
                else:
                    opkind = self.opkind.swapped_opkind

            if reassembler != 'swap':
                if not opkind and not self.opkind.commutative:
                    if strict:
                        raise ValueError(
                            f'{self.opkind.name} operation is ' + (
                                'noncommutative',
                                'neither swappable nor commutative'
                            )[reassembler == 'generic']
                        )
                else:
                    opkind = self.opkind
            if not opkind:
                ret = self
            if not fn or reassembler == 'commutate':
                fn = reversed
            objects = fn(self.objects)

        elif isinstance(reassembler, OpKind) or Op.is_name(reassembler):
            opkind = reassembler
            if isinstance(opkind, OpKind):
                opkind = opkind.name
            head, *tail = self.objects
            objects = head, *map(self.conversions.fetch(self.opkind.name, opkind), tail)
        else:
            raise ValueError(f'unknown reorder type: {reassembler!r}')

        if ret is None:
            ret = type(self)(opkind, *objects)
        return ret

    def __repr__(self):
        opkind, objects = self.opkind, self.objects
        repr_string = opkind.repr.format(*objects)
        if self.chained:
            repr_string = functools.reduce(
                opkind.repr.format,
                objects[opkind.nargs::],
                repr_string
            )
        return repr_string

    def __len__(self):
        return len(self.objects)


@as_object.register(Object)
def identity(obj):
    return obj


class Symbol(Dataclass, Object):
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
