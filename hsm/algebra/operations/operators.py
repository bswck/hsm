from __future__ import annotations

import functools
import math
import operator
import weakref
import typing

from hsm import errors
from hsm import util

if typing.TYPE_CHECKING:
    from hsm.util.oop import MissingT
    from hsm.algebra.operations.operands import AtomicOperand
    from hsm.algebra.operations.operands import AtomicOperation
    from hsm.algebra.operations.operands import CompoundOperation


__all__ = (
    'Operator',

    'CustomFunction',  # base: Operator
    'ArithmeticOperator',  # base: Operator
    'Addition',  # base: ArithmeticOperator
    'Subtraction',  # base: ArithmeticOperator
    'Multiplication',  # base: ArithmeticOperator
    'Minus',  # base: ArithmeticOperator
    'Division',  # base: ArithmeticOperator
    'Exponentiation',  # base: ArithmeticOperator
    'Root',  # base: ArithmeticOperator
    'Modulus',  # base: ArithmeticOperator
    'Relation',  # base: Operator
    'In',  # base: Relation
    'NotIn',  # base: Relation
    'SubsetOf',  # base: Relation
    'ProperSubsetOf',  # base: Relation
    'BooleanRelation',  # base: Relation
    'And',  # base: BooleanRelation
    'Or',  # base: BooleanRelation
    'ExclusiveOr',  # base: BooleanRelation
    'Negate',  # base: BooleanRelation
    'Comparison',  # base: Relation
    'Equal',  # base: Comparison
    'Inequal',  # base: Comparison
    'GreaterEqual',  # base: Comparison
    'GreaterThan',  # base: Comparison
    'LessEqual',  # base: Comparison
    'LessThan',  # base: Comparison
    'In',  # base: Comparison
    'NotIn',  # base: Comparison
    'SubsetOf',  # base: Comparison
    'ProperSubsetOf',  # base: Comparison
    'ApproximatelyEqual',  # base: Comparison
)


class Operator:
    """
    Used for building operations.

    op.abs(x)
    -> op(op.abs, x)
    -> AtomicOperationExpression(operator=op.abs, operands=(x,))
    """

    name: str | None = None

    long_name: typing.ClassVar[str | None] = None
    min_args: typing.ClassVar[int | None] = None
    max_args: typing.ClassVar[int | float | None] = None
    priority: typing.ClassVar[int] = 0
    associative: typing.ClassVar[bool | None] = False
    commutative: typing.ClassVar[bool] = False
    comparison: typing.ClassVar[bool] = False
    chainable: typing.ClassVar[bool | None] = None
    swapped: typing.ClassVar[str | None] = None
    evaluates_to_bool: typing.ClassVar[bool] = False
    idempotent: typing.ClassVar[bool] = False
    distributes_over: typing.ClassVar[set[type[Operator]]] = None
    distributivity_offset: typing.ClassVar[int] = 0

    _swapped_cls: typing.ClassVar[type[Operator] | None] = None

    _classes = {}
    _instances = weakref.WeakValueDictionary()

    @util.oop.smart_initializer
    def __init__(self, name=None):
        self.name = name

    @util.oop.idempotent
    @util.oop.factory_constructor
    def __new__(cls, name):
        if cls != Operator:
            return object.__new__(cls)
        try:
            factory = cls._classes[name]
        except KeyError:
            raise errors.NoSuchOperation(
                f'{name!r}. Register operations by subclassing {cls.__qualname__}'
            ) from None
        return factory(name)

    def __call__(
            self,
            o1: AtomicOperand | AtomicOperation | CompoundOperation,
            o2: (
                    AtomicOperand | AtomicOperation
                    | CompoundOperation | MissingT
            ) = util.oop.MISSING,
            *,
            O: type[AtomicOperation],
            CO: type[CompoundOperation],
    ):
        if o2 is util.oop.MISSING:  # cases 1.1-1.3
            if o1.is_A:
                return O(self, o1)  # case 1.1
            if o1.operator is self and (o1.is_O or o1.is_CO) and self.idempotent:
                return o1  # case 1.2
            return CO(self, o1)  # case 1.3

        if o1.is_A and o2.is_A:
            return O(self, o1, o2)  # case 2

        o1_so = o1.is_A or o1.operator is self  # o1: is it the same operator?
        o2_so = o2.is_A or o2.operator is self  # o2: is it the same operator?
        associative = self.associative  # speed

        if o1_so or o2_so:  # cases 3-10
            if o1.is_A and o2_so and associative:  # cases 3-4
                if o2.is_O:
                    return O(self, o1, *o2.operands)  # case 3
                if o2.is_CO:
                    return CO(self, o1, *o2.operands)  # case 4
            elif o2.is_A and o1_so:
                if o1.is_O:
                    return O(self, *o1.operands, o2)  # case 5
                if o1.is_CO:
                    return CO(self, *o1.operands, o2)  # case 8
            elif not (o1.is_A or o2.is_A):
                if associative and o2_so:
                    if o1.is_O and o1_so and o2.is_O:
                        return O(self, *o1.operands, *o2.operands)  # case 6
                    if o1_so:
                        return CO(self, *o1.operands, *o2.operands)  # cases 6, 7, 9, 10
                    return CO(self, o1, *o2.operands)  # cases 6, 7, 9, 10
                if o1_so:
                    return CO(self, *o1.operands, o2)  # cases 6, 7, 9, 10

        return CO(self, o1, o2)  # common case: inassociative and/or some Op is of different kind

    def compute_func(self, o1, o2, *, op, O, CO, **kwargs):
        raise NotImplementedError

    def compute(self, operation, context, *, op, O, CO, **kwargs):
        self.validate_operation(operation, operation.operands)
        kwargs.update(op=op, O=O, CO=CO)
        try:
            o1 = operation.operands[0].compute(context, **kwargs)
            if len(operation.operands) == 1:
                return self.compute_func(o1, **kwargs)
            return functools.reduce(
                functools.partial(self.compute_func, **kwargs),
                map(
                    operator.methodcaller('compute', context, **kwargs),
                    operation.operands[1:]
                ),
                o1
            )
        except NotImplementedError:
            raise NotImplementedError(f'cannot compute {self.long_name}') from None

    def validate_operation(
            self,
            operation,
            operands=None,
            allowed_types=None
    ):
        if operation.operator is not self:
            raise TypeError(
                f'incorrect operator for {operation.operator.long_name}: {self.long_name}'
            )
        if operands is None:
            return
        nargs = len(operands)
        if self.min_args is not None:
            min_args = self.min_args
            max_args = self.max_args
            if nargs < min_args:
                raise ValueError(
                    f'too few arguments for {self.long_name} '
                    f'(expected at least {min_args}, got {nargs})'
                )
            if nargs > max_args:
                if not self.chainable:
                    raise ValueError(
                        f'{self.long_name} operation is not chainable '
                        f'(too many arguments passed, maximally {max_args} accepted)'
                    )
                operation.chained = True
        if allowed_types:
            for operand in operands:
                if not isinstance(operand, allowed_types):
                    raise TypeError(
                        f'invalid operand type for {type(operation).__name__} '
                        f'{self.name}: {type(operand).__name__!r}'
                    )

    @classmethod
    def _setup_swapped_ops(cls):
        swapped_name = cls.swapped
        swapped_cls = cls._swapped_cls
        if swapped_cls:
            cls.swapped = swapped_cls.name
            swapped_cls._swapped_cls = cls
        elif swapped_name:
            swapped_cls = cls._classes.get(swapped_name)
            if swapped_cls:
                swapped_cls.swapped_name = cls.name
                swapped_cls.swapped_cls = cls
            cls._swapped_cls = swapped_cls

    @classmethod
    def _setup_operand_quantity(cls):
        if cls.chainable is None:
            if cls.min_args is None:
                cls.chainable = False
            else:
                cls.chainable = cls.min_args > 1
        if cls.max_args is None:
            cls.max_args = float('inf')

    def __init_subclass__(cls, **kwargs):
        if not isinstance(cls.name, str) or not cls.name:
            return
        if not cls.long_name:
            cls.long_name = cls.name
        cls._classes[cls.name] = cls
        cls._setup_swapped_ops()
        cls._setup_operand_quantity()
        if cls.distributes_over is None:
            cls.distributes_over = set()

    def __repr__(self):
        return f'op.{self.name.replace(" ", "_")}'


distributes_over = util.oop.marker('distributes_over', lambda c, t, v: getattr(c, t).add(v))


class CustomFunction(Operator):
    priority = float('inf')


class ArithmeticOperator(Operator, interface=False):
    priority = 0
    min_args = 2
    max_args = None


class Addition(ArithmeticOperator):
    name = 'add'
    long_name = 'addition'
    associative = True
    commutative = True
    priority = 0

    def compute_func(self, o1, o2, *, op, O, CO, **kwargs):
        return o1 + o2


class Subtraction(Addition):
    name = 'sub'
    long_name = 'subtraction'
    associative = False
    commutative = False

    def compute_func(self, o1, o2, *, op, O, CO, **kwargs):
        return o1 - o2


@distributes_over(Addition)
class Multiplication(ArithmeticOperator):
    name = 'mul'
    long_name = 'multiplication'
    associative = True
    commutative = True
    priority = Addition.priority + 1

    def compute_func(self, o1, o2, *, op, O, CO, **kwargs):
        return o1 * o2


class Minus(Multiplication):
    name = 'minus'
    min_args = max_args = 1

    def compute_func(self, o1, o2=None, **kwargs):
        return -o1


class Division(Multiplication):
    name = 'div'
    long_name = 'division'
    associative = False
    commutative = False

    def compute_func(self, o1, o2, *, op, O, CO, **kwargs):
        return o1 / o2


@distributes_over(Multiplication)
class Exponentiation(ArithmeticOperator):
    name = 'pow'
    long_name = 'exponentiation'
    chainable = False
    priority = Multiplication.priority + 1

    def compute_func(self, o1, o2, *, op, O, CO, **kwargs):
        return o1 ** o2


class Root(Exponentiation):
    name = long_name = 'root'

    def compute_func(self, o1, o2, *, op, O, CO, **kwargs):
        from hsm.algebra.operations.operands import ExpressionOperand
        return o1.root(o2) if isinstance(o1, ExpressionOperand) else o1 ** (1 / o2)


@distributes_over(Multiplication)
class Modulus(ArithmeticOperator):
    name = 'abs'
    long_name = 'modulus'
    idempotent = True
    min_args = max_args = 1
    priority = Exponentiation.priority + 1

    def compute_func(self, o1, o2=None, **kwargs):
        from hsm.algebra.operations.operands import ExpressionOperand
        return o1.abs() if isinstance(o1, ExpressionOperand) else abs(o1)


class Relation(Operator, interface=False):
    priority = float('inf')
    associative = False
    evaluates_to_bool = True
    min_args = 2
    max_args = None


class Comparison(Relation, interface=False):
    comparison = True


class Equal(Comparison):
    name = 'eq'
    long_name = 'equality relation'
    commutative = True

    def compute_func(self, o1, o2, *, op, O, CO, **kwargs):
        return o1 == o2


class ApproximatelyEqual(Comparison):
    name = 'approx eq'
    long_name = 'approximate equality'

    def compute_func(self, o1, o2, *, abs_tol=None, rel_tol=None, **kwargs):
        return math.isclose(o1, o2, abs_tol=abs_tol, rel_tol=rel_tol)


class Inequal(Comparison):
    name = 'ne'
    long_name = 'inequality relation'
    commutative = True


class GreaterEqual(Comparison):
    name = 'ge'
    swapped = 'le'
    long_name = 'greater-or-equal inequality relation'


class GreaterThan(Comparison):
    name = 'gt'
    swapped = 'lt'
    long_name = 'greater-than inequality relation'


class LessEqual(Comparison):
    name = 'le'
    swapped = 'ge'
    long_name = 'less-or-equal inequality relation'


class LessThan(Comparison):
    name = 'lt'
    swapped = 'gt'
    long_name = 'less-than inequality relation'


class In(Relation):
    name = 'in'
    long_name = 'membership relation'


class NotIn(Relation):
    name = 'not in'
    long_name = 'negation of membership relation'


class SubsetOf(Relation):
    name = 'subset of'
    long_name = 'inclusion relation'


class ProperSubsetOf(Relation):
    name = 'proper subset of'
    long_name = 'proper inclusion relation'


class Union(Operator):
    name = 'union'


class Intersection(Operator):
    name = 'intersection'


class Difference(Operator):
    name = 'diff'
    long_name = 'set difference'


class BooleanRelation(Relation, interface=False):
    associative = True

    def validate_operation(self, operation, operands=None, allowed_types=None):
        super().validate_operation(operation, operands, allowed_types)
        if operands is None:
            return
        nonboolean = []
        for operand in operands:
            if not operand.evaluates_to_bool:
                nonboolean.append(repr(operand) + f' ({operand.name})')
        if nonboolean:
            raise ValueError(
                f'non-boolean operand(s) for {self.long_name!r}: {", ".join(nonboolean)}'
            )


class Negate(BooleanRelation):
    name = 'neg'
    min_args = max_args = 1
    long_name = 'logical negation'


class And(BooleanRelation):
    name = 'and'
    commutative = True
    long_name = 'conjunction'


class Or(BooleanRelation):
    name = 'or'
    commutative = True
    long_name = 'disjunction'


class ExclusiveOr(BooleanRelation):
    name = 'xor'
    commutative = True
    long_name = 'exclusive disjunction'
