from hsm.ops.operation import Operation


class ArithmeticOperation(Operation):
    priority = 0
    min_args = 2
    max_args = None


class Addition(ArithmeticOperation):
    name = 'add'
    full_name = 'addition'
    associative = True
    commutative = True
    priority = 0


class Subtraction(Addition):
    name = 'sub'
    full_name = 'subtraction'
    associative = False
    commutative = False


class Multiplication(ArithmeticOperation):
    name = 'mul'
    full_name = 'multiplication'
    associative = True
    commutative = True
    priority = Addition.priority + 1


class Unary(Multiplication):
    name = 'unary'
    min_args = max_args = 1
    

class Division(Multiplication):
    name = 'div'
    full_name = 'division'
    associative = False
    commutative = False
    

class Exponentiation(ArithmeticOperation):
    name = 'pow'
    full_name = 'power'
    chainable = False
    priority = Multiplication.priority + 1
    

class Root(Exponentiation):
    name = full_name = 'root'


class Modulus(ArithmeticOperation):
    name = 'abs'
    full_name = 'modulus'
    idempotent = True
    min_args = max_args = 1
    priority = Exponentiation.priority + 1
    

class Relation(Operation):
    priority = float('inf')
    associative = False
    evaluates_to_bool = True
    min_args = 2
    max_args = None


class Comparison(Relation):
    comparison = True


class Equal(Relation):
    name = 'eq'
    full_name = 'equality relation'
    commutative = True
    

class Inequal(Comparison):
    name = 'ne'
    full_name = 'inequality relation'
    commutative = True
    

class GreaterEqual(Comparison):
    name = 'ge'
    swapped = 'le'
    full_name = 'greater-or-equal inequality relation'


class GreaterThan(Comparison):
    name = 'gt'
    swapped = 'lt'
    full_name = 'greater-than inequality relation'


class LessEqual(Comparison):
    name = 'le'
    swapped = 'ge'
    full_name = 'less-or-equal inequality relation'


class LessThan(Comparison):
    name = 'lt'
    swapped = 'gt'
    full_name = 'less-than inequality relation'


class In(Relation):
    name = 'in'
    full_name = 'membership relation'


class NotIn(In):
    name = 'not in'
    full_name = 'negation of membership relation'


class SubsetOf(Relation):
    name = 'subset of'
    full_name = 'inclusion relation'


class ProperSubsetOf(SubsetOf):
    name = 'proper subset of'
    full_name = 'proper inclusion relation'


class Union(Operation):
    name = 'union'


class Intersection(Operation):
    name = 'intersection'
    

class Difference(Operation):
    name = 'diff'
    full_name = 'set difference'


class ApproximatelyEqual(Relation):
    name = 'approx eq'
    full_name = 'approximate equation'


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
                f'non-boolean operand(s) for {self.full_name!r} relation: {", ".join(non_boolean)}'
            )


class Negate(BooleanRelation):
    name = 'neg'
    min_args = max_args = 1
    full_name = 'logical negation'


class And(BooleanRelation):
    name = 'and'
    commutative = True
    full_name = 'logical AND - conjunction'


class Or(BooleanRelation):
    name = 'or'
    commutative = True
    full_name = 'logical OR - disjunction'


class ExclusiveOr(BooleanRelation):
    name = 'xor'
    commutative = True
    full_name = 'logical XOR - exclusive disjunction'


class Function(Operation):
    priority = float('inf')
