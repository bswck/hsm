from hsm.arith.base import Arithmetic


class Operation(Arithmetic):
    priority = 0
    min_args = 2
    max_args = None


class Addition(Operation):
    name = 'add'
    associative = True
    commutative = True
    priority = 0


class Subtraction(Addition):
    name = 'sub'
    associative = False
    commutative = False


class Multiplication(Operation):
    name = 'mul'
    associative = True
    commutative = True
    priority = Addition.priority + 1


class Unary(Multiplication):
    name = 'unary'
    min_args = max_args = 1
    

class Division(Multiplication):
    name = 'div'
    associative = False
    commutative = False
    

class Exponentiation(Operation):
    name = 'pow'
    chainable = False
    priority = Multiplication.priority + 1
    

class Root(Exponentiation):
    name = 'root'
    

class AbsoluteValue(Operation):
    name = 'abs'
    min_args = max_args = 1
    priority = Exponentiation.priority + 1
    

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
    

class Inequal(Comparison):
    name = 'ne'
    commutative = True
    

class GreaterEqual(Comparison):
    name = 'ge'
    swapped = 'le'
    

class GreaterThan(Comparison):
    name = 'gt'
    swapped = 'lt'
    

class LessEqual(Comparison):
    name = 'le'
    swapped = 'ge'
    

class LessThan(Comparison):
    name = 'lt'
    swapped = 'gt'
    

class In(Relation):
    name = 'in'
    

class NotIn(In):
    name = 'not in'
    

class SubsetOf(Relation):
    name = 'subset of'
    

class ProperSubsetOf(SubsetOf):
    name = 'proper subset of'
    

class Union(Arithmetic):
    name = 'union'
    

class Intersection(Arithmetic):
    name = 'intersection'
    

class Difference(Arithmetic):
    name = 'diff'
    

class ApproximatelyEqual(Relation):
    name = 'approx eq'
    

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
    

class And(BooleanRelation):
    name = 'and'
    commutative = True
    

class Or(BooleanRelation):
    name = 'or'
    commutative = True
    

class ExclusiveOr(BooleanRelation):
    name = 'xor'
    commutative = True
    

class FunctionArithmetic(Arithmetic):
    priority = float('inf')
