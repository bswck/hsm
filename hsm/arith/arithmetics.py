from hsm.arith.arithmetic import Arithmetic
from hsm.arith.repr import PythonReprEngine
from hsm.arith.repr import infix_operator


class Operation(Arithmetic):
    priority = 0
    min_args = 2
    max_args = None


class Addition(Operation):
    name = 'add'
    associative = True
    commutative = True
    priority = 0
    repr_engine = infix_operator('+')


class Subtraction(Addition):
    name = 'sub'
    associative = False
    commutative = False
    repr_engine = infix_operator('-')


class Multiplication(Operation):
    name = 'mul'
    associative = True
    commutative = True
    priority = Addition.priority + 1
    repr_engine = infix_operator('*')


class Division(Multiplication):
    name = 'div'
    associative = False
    commutative = False
    repr_engine = infix_operator('/')


class Exponentiation(Operation):
    name = 'pow'
    chainable = False
    priority = Multiplication.priority + 1
    repr_engine = infix_operator('^')


class Root(Exponentiation):
    name = 'root'
    repr_engine = PythonReprEngine('{0}^(1/{1})', 'composition')


class AbsoluteValue(Operation):
    name = 'abs'
    min_args = max_args = 1
    priority = Exponentiation.priority + 1
    repr_engine = PythonReprEngine('|{0}|', 'composition', priority_parenthesization=False)


class Relation(Arithmetic):
    priority = float('inf')
    associative = False
    evaluates_to_bool = True
    min_args = 2
    max_args = None


class Comparison(Relation):
    comparison = True


class Equal(Relation):
    name = 'eq'
    commutative = True
    repr_engine = infix_operator('=', priority_parenthesization=False)


class Inequal(Comparison):
    name = 'ne'
    commutative = True
    repr_engine = infix_operator('!=', priority_parenthesization=False)


class GreaterEqual(Comparison):
    name = 'ge'
    swapped = 'le'
    repr_engine = infix_operator('>=', priority_parenthesization=False)


class GreaterThan(Comparison):
    name = 'gt'
    swapped = 'lt'
    repr_engine = infix_operator('>', priority_parenthesization=False)


class LessEqual(Comparison):
    name = 'le'
    swapped = 'ge'
    repr_engine = infix_operator('<=', priority_parenthesization=False)


class LessThan(Comparison):
    name = 'lt'
    swapped = 'gt'
    repr_engine = infix_operator('<', priority_parenthesization=False)


class In(Relation):
    name = 'in'
    repr_engine = infix_operator('∈', priority_parenthesization=False)


class NotIn(In):
    name = 'not in'
    repr_engine = infix_operator('∉', priority_parenthesization=False)


class SubsetOf(Relation):
    name = 'subset of'
    repr_engine = infix_operator('⊂', priority_parenthesization=False)


class ProperSubsetOf(SubsetOf):
    name = 'proper subset of'
    repr_engine = infix_operator('⊊', priority_parenthesization=False)


class Union(Arithmetic):
    name = 'union'
    repr_engine = infix_operator('∪', priority_parenthesization=False)


class Intersection(Arithmetic):
    name = 'intersection'
    repr_engine = infix_operator('∩', priority_parenthesization=False)


class Difference(Arithmetic):
    name = 'diff'
    repr_engine = infix_operator('\\', priority_parenthesization=False)


class ApproximatelyEqual(Relation):
    name = 'approx eq'
    repr_engine = infix_operator('≈', priority_parenthesization=False)


class BooleanRelation(Relation):
    associative = True

    def validate_operands(self, operation, operands, allowed_types):
        super().validate_operands(operation, operands, allowed_types)
        non_boolean = []
        for operand in operands:
            if not operand.evaluates_to_bool:
                non_boolean.append(repr(operand) + f' ({operand.name})')
        if non_boolean:
            raise ValueError(
                f'non-boolean operand(s) for {self.name!r} relation: {", ".join(non_boolean)}'
            )


class Negate(BooleanRelation):
    name = 'neg'
    min_args = max_args = 1
    repr_engine = PythonReprEngine('¬{0}', 'composition')


class And(BooleanRelation):
    name = 'and'
    commutative = True
    repr_engine = infix_operator('∧', parentheses=True)


class Or(BooleanRelation):
    name = 'or'
    commutative = True
    repr_engine = infix_operator('∨', parentheses=True)


class ExclusiveOr(BooleanRelation):
    name = 'xor'
    commutative = True
    repr_engine = infix_operator('⊻', parentheses=True)


class FunctionArithmetic(Arithmetic):
    priority = float('inf')

    @property
    def repr_engine(self):
        return PythonReprEngine(f'{self.name}({{0}})', 'listing')
