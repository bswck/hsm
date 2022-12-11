import functools
import numbers

from hsm.arith.scheme import OperationScheme
from hsm.toolkit import Dataclass, _Sentinel
from hsm.toolkit import MISSING
from hsm.toolkit import Argument
from hsm.toolkit import Arguments
from hsm.toolkit import Parameter
from hsm.toolkit import Coercion
from hsm.toolkit import coercion_factory


@functools.singledispatch
def hsm_operand(value):
    raise ValueError(f'value {value!r} could not be recognised as an hsm operand')


class Operand:
    # Greetings, sympy authors    
    is_A = False
    is_O = False
    is_CO = False   
    
    @staticmethod
    def join(scheme, operand_1, operand_2=MISSING):
        return op(scheme, operand_1, operand_2)

    def reduce_join(self, op_name, *operands):
        operands = list(operands)
        return functools.reduce(
            functools.partial(self.join, op_name),
            operands, operands.pop(0)
        )

    def __add__(self, other):
        return self.join('add', self, other)

    def __radd__(self, other):
        return self.join('add', other, self)

    add = __add__

    def __sub__(self, other):
        return self.join('sub', self, other)

    def __rsub__(self, other):
        return self.join('sub', other, self)

    sub = __sub__

    def __mul__(self, other):
        return self.join('mul', self, other)

    def __rmul__(self, other):
        return self.join('mul', other, self)

    mul = __mul__

    def __truediv__(self, other):
        return self.join('div', self, other)

    def __rtruediv__(self, other):
        return self.join('div', other, self)

    div = __truediv__

    def __floordiv__(self, other):
        return self.join('floordiv', self, other)

    def __rfloordiv__(self, other):
        return self.join('floordiv', other, self)

    floordiv = __floordiv__

    def __mod__(self, other):
        return self.join('mod', self, other)

    def __rmod__(self, other):
        return self.join('mod', other, self)

    mod = __mod__

    def __matmul__(self, other):
        return self.join('matmul', self, other)

    def __rmatmul__(self, other):
        return self.join('matmul', other, self)

    matmul = __matmul__

    def __pow__(self, other):
        return self.join('pow', self, other)

    def __rpow__(self, other):
        return self.join('pow', other, self)

    pow = __pow__

    def root(self, other):
        return self.join('root', self, other)

    def __eq__(self, other):
        return self.join('eq', self, other)

    eq = __eq__

    def __ne__(self, other):
        return self.join('ne', self, other)

    ne = __ne__

    def __ge__(self, other):
        return self.join('ge', self, other)

    ge = __ge__

    def __gt__(self, other):
        return self.join('gt', self, other)

    gt = __gt__

    def __le__(self, other):
        return self.join('le', self, other)

    le = __le__

    def __lt__(self, other):
        return self.join('lt', self, other)

    lt = __lt__

    def __and__(self, other):
        return self.join('and', self, other)

    def __rand__(self, other):
        return self.join('and', other, self)

    and_ = __and__

    def __or__(self, other):
        return self.join('or', self, other)

    def __ror__(self, other):
        return self.join('or', other, self)

    or_ = __or__

    def __xor__(self, other):
        return self.join('xor', self, other)

    def __rxor__(self, other):
        return self.join('xor', other, self)

    xor = __xor__

    def contains(self, other):
        return self.join('contains', self, other)

    def in_(self, other):
        return self.join('contains', other, self)

    def __getitem__(self, other):
        return self.join('get', self, other)

    get = __getitem__

    def abs(self):
        return self.join('abs', self)

    def __invert__(self, other):
        return self.join('invert', self)

    invert = __invert__

    def repr(self, parentheses=False):
        raise NotImplementedError


class Symbol(Dataclass):
    name: str = Parameter(default='x', factory_key=True)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)


def symbols(name_string):
    if name_string.isalpha():
        names = name_string
    else:
        names = name_string.replace(' ', ',').split(',')
    return tuple(map(AtomicNode, names))


@hsm_operand.register(numbers.Real)
@hsm_operand.register(Symbol)
@hsm_operand.register(str)
class AtomicNode(Operand, Dataclass):
    is_A = True
    const = False
    value: numbers.Real | Symbol = Parameter(factory_key=True)
    domain = Parameter(default='R', factory_key=True)
    priority = -1

    def _get_value(self, context):
        value = self.value
        if isinstance(value, Symbol):
            return context[value.name]
        return value

    def get_value(self, context=None):
        return self._get_value(context or {})

    def __hash__(self):
        # Since .value is hashable and every value of same hash produces same instance,
        # all objects AtomicNode(value, domain) for the equal value and domain are the same
        # instance. Thus, we can use ID of the instance as a relevant value-dependent hash
        # of the instance.
        return id(self)

    def __neg__(self):
        return AtomicNode(-self.value)

    def repr(self, parentheses=False):
        repr_string = str(self.value)
        if isinstance(self.value, numbers.Real) and self.value < 0:
            repr_string = repr_string.join('()')
        return repr_string

    if __debug__:
        def __repr__(self):
            return self.repr()


_ = 'abcdefghijklmnopqrstuvwxyz'
a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z = symbols(_)


@coercion_factory(lambda tp: Coercion(tp, cast=hsm_operand))
class AtomicOperation(Dataclass, Operand):
    is_O = True
    scheme: OperationScheme = Argument()
    operands: tuple[AtomicNode, ...] = Arguments(allow_hint_coercions=False)
    chained = False
    _const = False
    _allowed_types = AtomicNode

    def __post_init__(self):
        super().__post_init__()
        if all(obj.const for obj in self.operands):
            self._const = True
        self.scheme.validate_operands(self, self.operands, allowed_types=self._allowed_types)

    @property
    def const(self):
        return self._const

    @property
    def priority(self):
        return self.scheme.priority

    def repr(self, parentheses=False):
        return self.scheme.repr(self, self.operands, parentheses=parentheses)

    def __hash__(self):
        return hash(self.operands)

    if __debug__:
        def __repr__(self):
            return self.repr()


class CompoundOperation(AtomicOperation):
    is_O = False
    is_CO = True
    operands: 'tuple[AtomicOperation | CompoundOperation | AtomicNode, ...]' = Arguments(
        factory_key=True, allow_hint_coercions=False
    )

    def __post_init__(self):
        self._allowed_types = (AtomicNode, AtomicOperation, CompoundOperation)
        super().__post_init__()
        atomic_nodes = []
        atomic_ops = []
        compound_ops = []

        for operand in self.operands:
            if isinstance(operand, AtomicNode):
                atomic_nodes.append(operand)
            elif isinstance(operand, AtomicOperation):
                atomic_ops.append(operand)
            elif isinstance(operand, CompoundOperation):
                compound_ops.append(operand)

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
        if self.scheme.associative:
            return *self.atomic_nodes, *self.atomic_operations, *self.compound_operations
        return self.operands


def op(
    S: OperationScheme,
    o1: AtomicNode | AtomicOperation | CompoundOperation,
    o2: AtomicNode | AtomicOperation | CompoundOperation | _Sentinel = MISSING,
    *,
    O: type[AtomicOperation] = AtomicOperation,
    CO: type[CompoundOperation] = CompoundOperation,
):
    """
    Glossary
    --------
    To provide a summary of all return types as succintly as possible,
    some helper symbols and terms have been coined.

    A
        Atomic node A: sole mathematical object without any operation performed on it,
        for example: x, 1 or -102.6.
    i, j, k...
        Variable numbers used to indicate amount of operands in an operation.
    iA
        (Different or same) atomic nodes i times in a row.
    O(S, i)
        Domain: i ∈ <1, ∞)
        Same as O(S, iA); atomic operation with operation scheme S and k atomic nodes.
    CO(S, iA, jO)
        Domain: i ∈ <0, ∞) ∧ j <1, ∞)) ∨ (i ∈ <1, ∞) ∧ j <0, ∞)
        Compound operation k with operation scheme S.
    Operation scheme
        For example: + (addition). Consequently, example atomic
        addition operation could be O(+, k), meaning there are k atomic nodes added up together.
        For instance, a very specific case of pattern O(+, 3) is 1 + 2 + 3.
        8 * x + 3 + 4 would then be a specific case of CO(+, O(*, 2), 2A).
    @
        Associative operation scheme.
    S
        Either associative or non-associative operation scheme.

    Return types depending on the input operands
    --------------------------------------------
    Shortcuts used:
    * `A`, referring to :class:`AtomicNode`;
    * `O`, referring to :class:`AtomicOperation`;
    * `CO`, referring to :class:`CompoundOperation`.
    
    1. Atomic node A and atomic node A.
        A ? A returns O(?, 2),
        like l + m = l + m.

    2. Atomic node A and atomic operation O.
        A @ O(@, i) returns O(@, i+1),
        like l + (m + n) = l + m + n.

        Any other case returns CO(S, A, O).

    3. Atomic node A and compound operation CO.
        Note: CO(@, iA, jO(@, k)) does not exist.
        It would always be reduced to O(@, k+1); see also A @ O(@, k) in point 2.

        A @ CO(@, iA, ...) returns CO(@, (i+1)A, ...),
        like l + (m + n + o + (p / q)) = l + m + n + o + (p / q).

        Any other case returns CO(S, A, CO).

    4. Atomic operation O and atomic node A.
        O(@, i) @ A returns O(@, i+1),
        like (k + l) + m = k + l + m.

        Any other case returns CO(S, O, A).

    5. Atomic operation O and atomic operation O.
        O(@, i) @ O(@, j) returns O(@, i+j),
        like (l + m) + (n + o) = l + m + n + o.

        Any other case returns CO(S, O, O).

    6. Atomic operation O and compound operation CO.
        O(@, i) @ CO(@, jA, kO) returns CO(@, (i+j)A, kO),
        like (l + m) + (n + o + (p * q)) = l + m + n + o + (p * q).

        Any other case returns CO(S, O, CO).

    7. Compound operation CO and atomic node A.
        CO(@, iA, jO) @ A returns CO(@, (i+1)A, jO),
        like (l + m + n + (o / p)) + q = l + m + n + o + q + (p / q).       

        Any other case returns CO(S, CO, A).

    8. Compound operation CO and atomic operation O.
        CO(@, iA, jO) @ O(@, k) returns CO(@, (i+k)A, jO),
        like (l + m + (p * q)) + (n + o) = l + m + n + o + (p * q).

        Any other case returns CO(S, CO, O).

    9. Compound operation CO and compound operation CO.
        CO(@, iA, jO) @ CO(@, lA, mO) returns CO(@, (i+l)A, (j+m)O),
        like (l + m + (p * q)) + (r + s + (t * u)) = l + m + r + s + (p * q) + (t * u).
         
        Any other case returns CO(S, CO, CO).
    """
    S = OperationScheme(S)
    o1 = hsm_operand(o1)

    if o2 is MISSING:
        return O(S, o1) if o1.is_A else CO(S, o1)
    o2 = hsm_operand(o2)

    simplifiable = bool(
        S.associative
        and (o1.is_A or (o1.scheme.associative and (o1.scheme is S)))
        and (o2.is_A or (o2.scheme.associative and (o2.scheme is S)))
    )

    if o1.is_A:
        if o2.is_A:
            return O(S, o1, o2)

    if simplifiable:
        if o1.is_A:
            if o2.is_O:
                return O(S, o1, *o2.operands)
            if o2.is_CO:
                return CO(S, o1, *o2.complexity_sorted_operands)
        elif o1.is_O:
            if o2.is_A:
                return O(S, *o1.operands, o2)
            if o2.is_O:
                return O(S, *o1.operands, *o2.operands)
            if o2.is_CO:
                return CO(S, *o1.operands, *o2.complexity_sorted_operands)
        elif o1.is_CO:
            if o2.is_A:
                return CO(S, *o1.atomic_nodes, o2, *o1.atomic_operations, *o1.compound_operations)
            if o2.is_O:
                return CO(S, *o1.atomic_nodes, *o2.operands, *o1.atomic_operations)
            if o2.is_CO:
                return CO(
                    S, *o1.atomic_nodes, *o2.atomic_nodes,
                    *o1.atomic_operations, *o2.atomic_operations,
                    *o1.compound_operations, *o2.compound_operations
                )
    return CO(S, o1, o2)


@hsm_operand.register(AtomicNode)
@hsm_operand.register(AtomicOperation)
@hsm_operand.register(CompoundOperation)
def identity(obj):
    return obj
