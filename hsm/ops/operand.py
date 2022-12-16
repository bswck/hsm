import functools
import numbers

from hsm import toolkit
from hsm.ops.operation import Operation


@functools.singledispatch
def operand(value):
    raise ValueError(f'value {value!r} could not be recognised as an hsm operand')


class Operand:
    # Greetings, sympy authors    
    is_A = False
    is_O = False
    is_CO = False   
    
    @staticmethod
    def _op(Op, o1, o2=toolkit.MISSING):
        return op(Op, o1, o2)

    def reduce_join(self, Op, *operands):
        operands = list(operands)
        return functools.reduce(
            functools.partial(self._op, Op),
            operands, operands.pop(0)
        )

    def op(self, Op, other):
        return self._op(Op, self, other)

    def __add__(self, other):
        return self._op('add', self, other)

    def __radd__(self, other):
        return self._op('add', other, self)

    add = __add__

    def __sub__(self, other):
        return self._op('sub', self, other)

    def __rsub__(self, other):
        return self._op('sub', other, self)

    sub = __sub__

    def __mul__(self, other):
        return self._op('mul', self, other)

    def __rmul__(self, other):
        return self._op('mul', other, self)

    mul = __mul__

    def __truediv__(self, other):
        return self._op('div', self, other)

    def __rtruediv__(self, other):
        return self._op('div', other, self)

    div = __truediv__

    def __floordiv__(self, other):
        return self._op('floordiv', self, other)

    def __rfloordiv__(self, other):
        return self._op('floordiv', other, self)

    floordiv = __floordiv__

    def __mod__(self, other):
        return self._op('mod', self, other)

    def __rmod__(self, other):
        return self._op('mod', other, self)

    mod = __mod__

    def __matmul__(self, other):
        return self._op('matmul', self, other)

    def __rmatmul__(self, other):
        return self._op('matmul', other, self)

    matmul = __matmul__

    def __pow__(self, other):
        return self._op('pow', self, other)

    def __rpow__(self, other):
        return self._op('pow', other, self)

    pow = __pow__

    def root(self, other):
        return self._op('root', self, other)

    def __eq__(self, other):
        return self._op('eq', self, other)

    eq = __eq__

    def __ne__(self, other):
        return self._op('ne', self, other)

    ne = __ne__

    def __ge__(self, other):
        return self._op('ge', self, other)

    ge = __ge__

    def __gt__(self, other):
        return self._op('gt', self, other)

    gt = __gt__

    def __le__(self, other):
        return self._op('le', self, other)

    le = __le__

    def __lt__(self, other):
        return self._op('lt', self, other)

    lt = __lt__

    def __and__(self, other):
        return self._op('and', self, other)

    def __rand__(self, other):
        return self._op('and', other, self)

    and_ = __and__

    def __or__(self, other):
        return self._op('or', self, other)

    def __ror__(self, other):
        return self._op('or', other, self)

    or_ = __or__

    def __xor__(self, other):
        return self._op('pow', self, other)

    def __rxor__(self, other):
        return self._op('pow', other, self)

    def xor(self, other):
        return self._op('xor', self, other)

    def contains(self, other):
        return self._op('in', other, self)

    def in_(self, other):
        return self._op('in', self, other)

    def __getitem__(self, other):
        return self._op('get', self, other)

    get = __getitem__

    def abs(self):
        return self._op('abs', self)

    def __invert__(self, other):
        return self._op('invert', self)

    invert = __invert__

    def __neg__(self):
        return self._op('unary', self)


class Symbol(toolkit.Dataclass):
    name: str = toolkit.Parameter(default='x', factory_key=True)
    negative: bool = toolkit.Parameter(default=False, factory_key=True)

    def __repr__(self):
        if self.negative:
            return f'-{self.name}'
        return self.name

    def __neg__(self):
        return type(self)(self.name, negative=not self.negative)

    def __hash__(self):
        return hash(self.name)


def symbols(name_string):
    if name_string.isalpha():
        names = name_string
    else:
        names = name_string.replace(' ', ',').split(',')
    return tuple(map(AtomicOperand, names))


@operand.register(numbers.Real)
@operand.register(Symbol)
@operand.register(str)
class AtomicOperand(Operand, toolkit.Dataclass):
    value: Symbol | numbers.Real = toolkit.Parameter(factory_key=True)
    # domain = toolkit.Parameter(default='R', factory_key=True)

    is_A = True
    const = False
    priority = 0
    evaluates_to_bool = False
    operation = None
    _name = 'atomic'

    def __post_init__(self):
        if isinstance(self.value, bool):
            self.evaluates_to_bool = True

    @property
    def name(self):
        return self._name

    def _get_value(self, context):
        value = self.value
        if isinstance(value, Symbol):
            return context[value.name]
        return value

    def get_value(self, context=None):
        return self._get_value(context or {})

    def __hash__(self):
        # Since .value is hashable and every value of same hash produces same instance,
        # all objects AtomicOperand(value, domain) for the equal value and domain are the same
        # instance. Thus, we can use ID of the instance as a relevant value-dependent hash
        # of the instance.
        return id(self)

    def __neg__(self):
        return AtomicOperand(-self.value)


_ = 'abcdefghijklmnopqrstuvwxyz'
a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z = symbols(_)


@toolkit.coercion_factory(lambda tp: toolkit.Coercion(tp, cast=operand))
class AtomicOperationOperand(toolkit.Dataclass, Operand):
    operation: Operation = toolkit.Argument()
    operands: tuple[AtomicOperand, ...] = toolkit.Arguments(allow_hint_coercions=False)

    is_O = True
    chained = False
    _const = False
    _allowed_types = AtomicOperand

    def __post_init__(self):
        super().__post_init__()
        if all(obj.const for obj in self.operands):
            self._const = True
        self.operation.validate_operands(self, self.operands, allowed_types=self._allowed_types)

    @property
    def const(self):
        return self._const

    @property
    def name(self):
        return self.operation.name

    @property
    def evaluates_to_bool(self):
        return self.operation.evaluates_to_bool

    @property
    def priority(self):
        return self.operation.priority

    def __hash__(self):
        return hash(self.operands)

    def _repr_long(self):
        def mapper(name, item, ident=0):
            if name == 'operands':
                return toolkit.nested_repr_ident(item, ident=ident)
            return repr(item)

        return self.repr(ident=2, mapper=mapper)

    def __repr__(self):
        return self._repr_long()


class CompoundOperationOperand(AtomicOperationOperand):
    operands = toolkit.Arguments(
        factory_key=True, allow_hint_coercions=False
    )  # type: tuple[AtomicOperand | AtomicOperationOperand | CompoundOperationOperand, ...]

    is_O = False
    is_CO = True

    def __post_init__(self):
        self._allowed_types = (AtomicOperand, AtomicOperationOperand, CompoundOperationOperand)
        super().__post_init__()
        atomic_nodes = []
        atomic_ops = []
        compound_ops = []

        for oper in self.operands:
            if isinstance(oper, AtomicOperand):
                atomic_nodes.append(oper)
            elif isinstance(oper, AtomicOperationOperand):
                atomic_ops.append(oper)
            elif isinstance(oper, CompoundOperationOperand):
                compound_ops.append(oper)

        self._atomic_nodes = tuple(atomic_nodes)
        self._atomic_ops = tuple(atomic_ops)
        self._compound_ops = tuple(compound_ops)

    @property
    def atomic_nodes(self):
        return self._atomic_nodes

    @property
    def atomic_operations(self):
        return self._atomic_ops

    @property
    def compound_operations(self):
        return self._compound_ops

    @property
    def complexity_sorted_operands(self):
        if self.operation.associative:
            return *self.atomic_nodes, *self.atomic_operations, *self.compound_operations
        return self.operands


class _OpFunction:
    def __init__(self, fn):
        self.__op = fn

    def __call__(self, *args, **kwargs):
        if not args:
            raise TypeError(
                f'{self.__op.__qualname__}() missing 1 required positional argument: \'obj\''
            )
        if len(args) == 1 and not kwargs:
            obj, = args
            return operand(obj)
        Op, args, reduce = args[0], args[1:3], args[3:]
        initial = self.__op(Op, *args, **kwargs)
        if reduce:
            return functools.reduce(
                functools.partial(self.__op, Op, **kwargs),
                reduce, initial
            )
        return initial

    @staticmethod
    def _sanitize_attr_name(name):
        return name.replace('_', ' ').rstrip()

    def __getattr__(self, item):
        return functools.partial(self, Operation(self._sanitize_attr_name(item)))


@_OpFunction
def op(
    Op: Operation,
    o1: AtomicOperand | AtomicOperationOperand | CompoundOperationOperand,
    o2: AtomicOperand | AtomicOperationOperand | CompoundOperationOperand | toolkit._Sentinel = (
        toolkit.MISSING
    ),
    *,
    O: type[AtomicOperationOperand] = AtomicOperationOperand,
    CO: type[CompoundOperationOperand] = CompoundOperationOperand,
):
    """
    Glossary
    --------
    To provide a summary of all return types as succintly as possible,
    some helper symbols and terms have been coined.

    A
        Atomic operand A: sole mathematical object without any operation performed on it,
        for example: x, 1 or -102.6.
    i, j, k...
        Variable numbers used to indicate amount of operands in an operation.
    iA
        (Different or same) atomic operands i times in a row.
    O(Op, i)
        Domain: i ∈ <1, ∞)
        Same as O(S, iA); atomic operation operand with operation Op and k atomic operands.
    CO(Op, iA, jO)
        Domain: (i ∈ <0, ∞) ∧ j <1, ∞)) ∨ (i ∈ <1, ∞) ∧ j <0, ∞))
        Compound operation operand k with operation Op.
    Operation (Op)
        For example: + (addition). Consequently, example atomic
        addition operation could be O(+, k), meaning there are k atomic operands added up together.
        For instance, a very specific case of pattern O(+, 3) is 1 + 2 + 3.
        8 * x + 3 + 4 would then be a specific case of CO(+, O(*, 2), 2A).
    @
        Associative operation.

    Return types depending on the input operands
    --------------------------------------------
    Shortcuts used:
    * `A`, referring to :class:`AtomicOperand`;
    * `O`, referring to :class:`AtomicOperationOperand;
    * `CO`, referring to :class:`CompoundOperationOperand.
    
    1. Atomic operand A and atomic operand A.
        A Op A returns O(Op, 2),
        like l + m = l + m.

    2. Atomic operand A and atomic operation operand O.
        A @ O(@, i) returns O(@, i+1),
        like l + (m + n) = l + m + n.

        Any other case returns CO(Op, A, O).

    3. Atomic operand A and compound operation operand CO.
        Note: CO(@, iA, jO(@, k)) does not exist.
        It would always be reduced to O(@, k+1); see also A @ O(@, k) in point 2.

        A @ CO(@, iA, ...) returns CO(@, (i+1)A, ...),
        like l + (m + n + o + (p / q)) = l + m + n + o + (p / q).

        Any other case returns CO(Op, A, CO).

    4. Atomic operation operand O and atomic operand A.
        O(@, i) @ A returns O(@, i+1),
        like (k + l) + m = k + l + m.

        Any other case returns CO(Op, O, A).

    5. Atomic operation operand O and atomic operation operand O.
        O(@, i) @ O(@, j) returns O(@, i+j),
        like (l + m) + (n + o) = l + m + n + o.

        Any other case returns CO(Op, O, O).

    6. Atomic operation operand O and compound operation operand CO.
        O(@, i) @ CO(@, jA, kO) returns CO(@, (i+j)A, kO),
        like (l + m) + (n + o + (p * q)) = l + m + n + o + (p * q).

        Any other case returns CO(Op, O, CO).

    7. Compound operation operand CO and atomic operand A.
        CO(@, iA, jO) @ A returns CO(@, (i+1)A, jO),
        like (l + m + n + (o / p)) + q = l + m + n + o / p + q.

        Any other case returns CO(Op, CO, A).

    8. Compound operation operand CO and atomic operation operand O.
        CO(@, iA, jO) @ O(@, k) returns CO(@, (i+k)A, jO),
        like (l + m + (n * o)) + (p + q) = l + m + (n * o) + p + q.

        Any other case returns CO(Op, CO, O).

    9. Compound operation operand CO and compound operation operand CO.
        CO(@, iA, jO) @ CO(@, lA, mO) returns CO(@, (i+l)A, (j+m)O),
        like (l + m + (p * q)) + (r + s + (t * u)) = l + m + r + s + (p * q) + (t * u).
         
        Any other case returns CO(Op, CO, CO).
    """
    Op = Operation(Op)
    o1 = operand(o1)

    if o2 is toolkit.MISSING:
        if o1.is_A:
            return O(Op, o1)
        if o1.operation is Op and (o1.is_O or o1.is_CO) and Op.idempotent:
            return o1
        return CO(Op, o1)

    o2 = operand(o2)

    if o1.is_A:
        if o2.is_A:
            return O(Op, o1, o2)

    if Op.associative and (o1.operation is Op or o2.operation is Op):
        if o1.is_A:
            if o2.is_O:
                return O(Op, o1, *o2.operands)
            if o2.is_CO:
                return CO(Op, o1, *o2.operands)
        elif not (o1.is_A or o2.is_A):
            if o1.is_O and o2.is_O:
                return O(Op, *o1.operands, *o2.operands)
            if o1.operation is o2.operation is Op:
                return CO(Op, *o1.operands, *o2.operands)
            if o1.operation is Op:
                return CO(Op, *o1.operands, o2)
            if o2.operation is Op:
                return CO(Op, o1, *o2.operands)
        elif o1.is_O:
            if o2.is_A:
                return O(Op, *o1.operands, o2)
        elif o1.is_CO:
            if o2.is_A:
                return CO(Op, *o1.operands, o2)

    return CO(Op, o1, o2)


@operand.register(AtomicOperand)
@operand.register(AtomicOperationOperand)
@operand.register(CompoundOperationOperand)
def identity(obj):
    return obj
