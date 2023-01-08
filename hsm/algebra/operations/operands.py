from __future__ import annotations

import functools
import numbers
import string
import typing
import warnings

from hsm import util
from hsm.algebra.operations.operators import Operator


__all__ = (
    'ExpressionOperand',
    'AtomicOperand',
    'AtomicOperation',
    'CompoundOperation',
    'op',
    'operand',
    'Symbol',
    'symbols',
    *string.ascii_lowercase
)

_MISSING = util.oop.MISSING


@functools.singledispatch
def operand(value):
    """
    Cast any value to an operand that might be used in an expression.

    operand(5) -> AtomicExpression(value=5)
    operand('a') -> AtomicExpression(value=a)
    """
    if value is _MISSING:
        return value    
    raise ValueError(f'value {value!r} could not be recognised as an operand')


class ExpressionOperand:
    """
    Represents a chunk of a mathematical expression.

    Given expression a + b + c,
    a, b and c are operands - in this case, atomic operands.

    Given expression (a/b) + c + d,
    a/b, c and d are operands - in this case, 1 atomic operation and 2 atomic operands.
    """

    is_A: typing.ClassVar[bool] = False  # is this an atomic operand?
    is_O: typing.ClassVar[bool] = False  # is this an atomic operation?
    is_CO: typing.ClassVar[bool] = False  # is this a compound operation?

    __repr_hsm__ = False

    def _compute(self, context: dict, *, O, CO):
        """Compute this expression."""
        raise NotImplementedError

    def compute(self, context=None, O=None, CO=None, **context_kwargs):
        """Compute this expression."""
        if context is None:
            context = {}
        context.update(context_kwargs)
        return self._compute(
            context,
            op=op,
            O=AtomicOperation if O is None else O,
            CO=CompoundOperation if CO is None else CO,
        )

    @staticmethod
    def _op(Op, o1, o2=util.oop.MISSING, **kwargs):
        """Local op() wrapper for subclass-based configurability."""
        return op(Op, o1, o2, **kwargs)

    def op(self, Op, other=util.oop.MISSING, **kwargs):
        """
        self.op(Op) -> op(Op, self)
        self.op(Op, other) -> op(Op, self, other)
        """
        return self._op(Op, self, other, **kwargs)

    def __add__(self, other):
        """Return self + other."""
        return self._op('add', self, other)

    def __radd__(self, other):
        """Return other + self."""
        return self._op('add', other, self)

    add = __add__

    def __sub__(self, other):
        """Return self - other."""
        return self._op('sub', self, other)

    def __rsub__(self, other):
        """Return other - self."""
        return self._op('sub', other, self)

    sub = __sub__

    def __mul__(self, other):
        """Return self * other."""
        return self._op('mul', self, other)

    def __rmul__(self, other):
        """Return other * self."""
        return self._op('mul', other, self)

    mul = __mul__

    def __truediv__(self, other):
        """Return self / other."""
        return self._op('div', self, other)

    def __rtruediv__(self, other):
        """Return other / self."""
        return self._op('div', other, self)

    div = __truediv__

    def __floordiv__(self, other):
        """Return self // other."""
        return self._op('floordiv', self, other)

    def __rfloordiv__(self, other):
        """Return other // self."""
        return self._op('floordiv', other, self)

    floordiv = __floordiv__

    def __mod__(self, other):
        """Return self % other."""
        return self._op('mod', self, other)

    def __rmod__(self, other):
        """Return other % self."""
        return self._op('mod', other, self)

    mod = __mod__

    def __matmul__(self, other):
        """Return self @ other."""
        return self._op('matmul', self, other)

    def __rmatmul__(self, other):
        """Return other @ self."""
        return self._op('matmul', other, self)

    matmul = __matmul__

    def __pow__(self, other):
        """Return self ** other."""
        return self._op('pow', self, other)

    def __rpow__(self, other):
        """Return other ** self."""
        return self._op('pow', other, self)

    pow = __pow__

    def root(self, other):
        """Return other-th root of self."""
        return self._op('root', self, other)

    def __eq__(self, other):
        """Return self == other."""
        return self._op('eq', self, other)

    eq = __eq__

    def __ne__(self, other):
        """Return self != other."""
        return self._op('ne', self, other)

    ne = __ne__

    def __ge__(self, other):
        """Return self >= other."""
        return self._op('ge', self, other)

    ge = __ge__

    def __gt__(self, other):
        """Return self > other."""
        return self._op('gt', self, other)

    gt = __gt__

    def __le__(self, other):
        """Return self <= other."""
        return self._op('le', self, other)

    le = __le__

    def __lt__(self, other):
        """Return self < other."""
        return self._op('lt', self, other)

    lt = __lt__

    def __and__(self, other):
        """Return self ∧ other."""
        return self._op('and', self, other)

    def __rand__(self, other):
        """Return other ∧ self."""
        return self._op('and', other, self)

    and_ = __and__

    def __or__(self, other):
        """Return self ∨ other."""
        return self._op('or', self, other)

    def __ror__(self, other):
        """Return other ∨ self."""
        return self._op('or', other, self)

    or_ = __or__

    def __xor__(self, other):
        """Return self ⊻ other."""
        return self._op('pow', self, other)

    def __rxor__(self, other):
        """Return other ⊻ self."""
        return self._op('pow', other, self)

    def xor(self, other):
        """Return other ⊻ self."""
        return self._op('xor', self, other)

    def contains(self, other):
        """Return self contains? other."""
        return self._op('in', other, self)

    def in_(self, other):
        """Return self in? other."""
        return self._op('in', self, other)

    def __getitem__(self, other):
        """Return self[other]."""
        return self._op('get', self, other)

    get = __getitem__

    def abs(self):
        """Return |self|."""
        return self._op('abs', self)

    def __invert__(self, other):
        """Return ¬self."""
        return self._op('neg', self)

    neg = __invert__

    def __neg__(self):
        """Return -self."""
        return self._op('minus', self)


class Symbol:
    """
    Named symbol holder. Supports - (minus operation).

    Symbol('x') -> x
    Symbol('x') is Symbol('x') -> True
    Symbol('x', negative=True) -> -x
    -Symbol('x', negative=True) -> x
    """
    __new__ = util.oop.make_factory_constructor(lambda name, negate: (name, negate))

    def __init__(self, name='x', negate=False):
        self.name = name
        self.negate = negate

    @classmethod
    def from_string(cls, string, _negate=False, _suppress_bracket_warnings=False):
        if isinstance(string, cls):
            return cls(string.name, negate=_negate)
        if not isinstance(string, str):
            raise TypeError('Symbol.from_str(): str expected')
        if not _suppress_bracket_warnings and string.count('(') != string.count(')'):
            warnings.warn(
                f'inconsistent brackets in symbol string: {string!r}'
            )
            _suppress_bracket_warnings = True
        lb = string.startswith('(')
        rb = string.endswith(')')
        if lb or rb:
            if lb and rb:
                string = string[1:-1]
        if string.startswith('-'):
            new_string = string.lstrip('-')
            return cls.from_string(
                new_string,
                _negate=(_negate, not _negate)[(len(string) - len(new_string)) % 2],
                _suppress_bracket_warnings=_suppress_bracket_warnings
            )
        return cls(string, negate=_negate)

    def __repr__(self):
        if self.negate:
            return f'-{self.name}'
        return self.name

    def __neg__(self):
        return type(self)(self.name, negative=not self.negate)

    def __hash__(self):
        return id(self)


@operand.register(numbers.Real)
@operand.register(Symbol)
@operand.register(str)
class AtomicOperand(ExpressionOperand):
    """
    Atomic operand (A).

    Sole symbol or number: a, 10, -5.25.
    Used to build operation operations, such as a/10, a + b or a*(10/-5.25) and much more.
    """

    value: Symbol | numbers.Real

    is_A = True

    evaluates_to_bool: bool = False
    const: typing.ClassVar[bool] = False
    priority: typing.ClassVar[int] = 0
    operator: typing.ClassVar[Operator | None] = None

    _name: typing.ClassVar[str] = 'A'

    __new__ = util.oop.make_factory_constructor(lambda value: value)

    @util.oop.smart_initializer
    def __init__(self, value):
        if not isinstance(value, numbers.Real):
            value = Symbol.from_string(value)
        self.value = value
        if isinstance(self.value, bool):
            self.evaluates_to_bool = True

    @property
    def name(self):
        return self._name

    def __neg__(self):
        return type(self)(-self.value)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return repr(self.value)


def symbols(name_string):
    """
    Initialize series of named symbols from the name list.
    symbols('ab') -> (AtomicExpression(value=a), AtomicExpression(value=b))
    """
    if name_string.isalpha():
        names = name_string
    else:
        names = name_string.replace(' ', ',').split(',')
    return tuple(map(AtomicOperand, names))


_ = string.ascii_lowercase
globals().update(zip(_, symbols(_)))


class AtomicOperation(ExpressionOperand):
    """
    Atomic operation expression (O).

    Represents an operation on atomic operands only.
    Valid examples are a+b, 5/3, 8/5/7, x*2y (comprehended as x*2*y), but not 2+2-5, 8/(5/7) etc.
    """

    operator: Operator
    operands: tuple[AtomicOperand, ...]

    is_O = True
    chained = False
    _allowed_types = AtomicOperand

    def __init__(self, operator: Operator, *operands: AtomicOperand):
        self.operator = operator
        self.operands = operands
        self._constant_operands = []
        self._variable_operands = []
        if self.is_O:
            for atomic_operand in operands:
                if atomic_operand.const:
                    self._constant_operands.append(atomic_operand)
                else:
                    self._variable_operands.append(atomic_operand)
        self.operator.validate_operation(
            self, self.operands,
            allowed_types=self._allowed_types
        )

    @property
    def name(self):
        return self.operator.name

    @property
    def constant_operands(self):
        return self._constant_operands

    @property
    def variable_operands(self):
        return self._variable_operands

    @property
    def evaluates_to_bool(self):
        return self.operator.evaluates_to_bool

    @property
    def priority(self):
        return self.operator.priority

    def __hash__(self):
        return hash(self.operands)

    def __repr__(self):
        def mapper(name, item, ident=2):
            if name == 'operands':
                return util.repr.repr_collection(
                    item, ident=ident, split=lambda result: len(result) > 120
                )
            return util.repr.repr_object(item)
        return util.repr.repr_object(
            self,
            attributes=['operands'],
            ident=2,
            prefix=self.name,
            mapper=mapper, split=True, ignore_flag=True
        )  # + '...' + ('co', 'o')[self.is_O]


class CompoundOperation(AtomicOperation):
    """
    Compound operation expression (CO).

    May represent any mathematical expression of indefinite complexity.
    Whenever an expression can be atomic due to associativity, it is not created as a compound
    expression. For example, a+(b+c) is not CO(+, a, O(+, b, c)), but O(+, a, b, c), because
    addition is associative. However, a/(b/c) is indeed CO(/, a, O(/, b, c)), because a/b/c
    and a/(b/c) is not semantically the same (not always equal, for real numbers a, b and c).
    """

    operands: tuple[AtomicOperand | AtomicOperation | CompoundOperation, ...]
    _allowed_types: typing.ClassVar[tuple[type[ExpressionOperand], ...]] = ()

    is_O = False
    is_CO = True

    def __init__(self, *operands: AtomicOperand | AtomicOperation | CompoundOperation):
        super().__init__(*operands)

        atomic_nodes = []
        atomic_ops = []
        compound_ops = []

        for opd in self.operands:
            if opd.is_A:
                atomic_nodes.append(opd)
            elif opd.is_O:
                atomic_ops.append(opd)
            elif opd.is_CO:
                compound_ops.append(opd)

        self._atomic_nodes = tuple(atomic_nodes)
        self._atomic_ops = tuple(atomic_ops)
        self._compound_ops = tuple(compound_ops)

    @property
    def atomic_nodes(self) -> tuple[AtomicOperand, ...]:
        """Atomic nodes in this operation."""
        return self._atomic_nodes

    @property
    def atomic_operations(self) -> tuple[AtomicOperation, ...]:
        """Atomic nodes in this operation."""
        return self._atomic_ops

    @property
    def compound_operations(self) -> tuple[CompoundOperation, ...]:
        return self._compound_ops


@operand.register(AtomicOperand)
@operand.register(AtomicOperation)
@operand.register(CompoundOperation)
def identity(obj):
    """When casting an operand to operand, return the identical operand."""
    return obj


class _OpFunctionAPI:
    """Private op() decorator for op.<custom op name>(o1[, o2]) syntax."""

    def __init__(self, fn):
        self.__op = fn

    def __call__(self, *args, **kwargs):
        """
        Call the op() function. Given 1 argument, cast it to an operand.

        op('x') -> AtomicNodeOperand(value=x)
        """
        if not args:
            raise TypeError(
                f'{self.__op.__qualname__}() missing 1 required positional argument: \'obj\''
            )
        if len(args) == 1 and not kwargs:
            obj, = args
            return operand(obj)
        Op, args, reduce = Operator(args[0]), args[1:3], args[3:]
        initial = self.__op(Op, *args, **kwargs)
        if reduce:
            return functools.reduce(
                functools.partial(self.__op, Op, **kwargs),
                reduce, initial
            )
        return initial

    @staticmethod
    def _sanitize_attr_name(name: str) -> str:
        """
        op.in_(a, X) -> op('in', a, X)
        op.subset_of(B, A) -> op('subset of', B, A)
        """
        return name.replace('_', ' ').rstrip()

    def __getattr__(self, item: str):
        """op.abs(1, 2) -> op('abs', 1, 2)"""
        return functools.partial(self, Operator(self._sanitize_attr_name(item)))


@_OpFunctionAPI
def op(
    Op: Operator,
    o1: AtomicOperand | AtomicOperation | CompoundOperation,
    o2: (
            AtomicOperand | AtomicOperation
            | CompoundOperation | util.oop.MissingT
    ) = util.oop.MISSING,
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
    Operator (Op)
        For example: + (addition). Consequently, example atomic
        addition operation could be O(+, k), meaning there are k atomic operands added up together.
        For instance, a very specific case of pattern O(+, 3) is 1 + 2 + 3.
        8 * x + 3 + 4 would then be a specific case of CO(+, O(*, 2), 2A).
    @
        Associative operation.

    Return types depending on the input operands
    --------------------------------------------
    Shortcuts used:
    * `A`, referring to :class:`AtomicExpression`.
    * `O`, referring to :class:`AtomicOperation`.
    * `CO`, referring to :class:`CompoundOperation`.

    1. Sole operand A, O or CO.
        1.1. Atomic operand A: O(Op, A)
        2.2. Idempotent operation O or CO: same O or CO.
        3.3. Any other case, O or CO: CO(Op, O or CO).

    2. Atomic operand A and atomic operand A.
        A Op A returns O(Op, 2),
        like l + m = l + m.

    3. Atomic operand A and atomic operation operand O.
        A @ O(@, i) returns O(@, i+1),
        like l + (m + n) = l + m + n.

        Any other case returns CO(Op, A, O).

    4. Atomic operand A and compound operation operand CO.
        Note: CO(@, iA, jO(@, k)) does not exist.
        It would always be reduced to O(@, k+1); see also A @ O(@, k) in point 2.

        A @ CO(@, iA, ...) returns CO(@, (i+1)A, ...),
        like l + (m + n + o + (p / q)) = l + m + n + o + (p / q).

        Any other case returns CO(Op, A, CO).

    5. Atomic operand O and atomic operand A.
        O(@, i) @ A returns O(@, i+1),
        like (k + l) + m = k + l + m.

        Any other case returns CO(Op, O, A).

    6. Atomic operand O and atomic operation operand O.
        O(@, i) @ O(@, j) returns O(@, i+j),
        like (l + m) + (n + o) = l + m + n + o.

        Any other case returns CO(Op, O, O).

    7. Atomic operand O and compound operation operand CO.
        O(@, i) @ CO(@, jA, kO) returns CO(@, (i+j)A, kO),
        like (l + m) + (n + o + (p * q)) = l + m + n + o + (p * q).

        Any other case returns CO(Op, O, CO).

    8. Compound operation operand CO and atomic operand A.
        CO(@, iA, jO) @ A returns CO(@, (i+1)A, jO),
        like (l + m + n + (o / p)) + q = l + m + n + o / p + q.

        Any other case returns CO(Op, CO, A).

    9. Compound operation operand CO and atomic operation operand O.
        CO(@, iA, jO) @ O(@, k) returns CO(@, (i+k)A, jO),
        like (l + m + (n * o)) + (p + q) = l + m + (n * o) + p + q.

        Any other case returns CO(Op, CO, O).

    10. Compound operation operand CO and compound operation operand CO.
        CO(@, iA, jO) @ CO(@, lA, mO) returns CO(@, (i+l)A, (j+m)O),
        like (l + m + (p * q)) + (r + s + (t * u)) = l + m + r + s + (p * q) + (t * u).
         
        Any other case returns CO(Op, CO, CO).
    """
    return Op(operand(o1), operand(o2), O=O, CO=CO)
