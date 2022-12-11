from hsm.arith.scheme import OperationScheme


class Addition(OperationScheme):
    name = 'add'
    associative = True
    commutative = True
    priority = 0
    fmt = '{0} + {1}'


class Subtraction(Addition):
    name = 'sub'
    associative = False
    commutative = False
    fmt = '{0} - {1}'


class Multiplication(OperationScheme):
    name = 'mul'
    associative = True
    commutative = True
    priority = Addition.priority + 1
    fmt = '{0} * {1}'


class Division(Multiplication):
    name = 'div'
    associative = False
    commutative = False
    fmt = '{0} / {1}'


class Exponentiation(OperationScheme):
    name = 'pow'
    chainable = False
    priority = Multiplication.priority + 1
    fmt = '{0} ^ {1}'


class Root(Exponentiation):
    name = 'root'
    fmt = '{0} ^ (1/{1})'


class AbsoluteValue(OperationScheme):
    name = 'abs'
    nargs = 1
    priority = Exponentiation.priority + 1
    fmt = '|{0}|'

    def repr(self, op, objects, parentheses=False):
        return self.fmt.format(objects[0].repr(parentheses=False))


class BooleanOperationScheme(OperationScheme):
    priority = float('inf')
    # That would be invalid unless we treat booleans like numbers, but that's so CS-specific!
    associative = None


class RequiresBooleanOperands:
    name: str

    def validate_objects(self, _, objects):
        if not all(isinstance(obj, BooleanOperationScheme) for obj in objects):
            raise ValueError(f'{self.name} operation on non-formula objects')


class Equal(BooleanOperationScheme):
    name = 'eq'
    commutative = True
    comparison = True
    fmt = '{0} == {1}'


class Inequal(BooleanOperationScheme):
    name = 'ne'
    commutative = True
    comparison = True
    fmt = '{0} != {1}'


class GreaterEqual(BooleanOperationScheme):
    name = 'ge'
    swapped = 'le'
    comparison = True
    fmt = '{0} >= {1}'


class GreaterThan(BooleanOperationScheme):
    name = 'gt'
    swapped = 'lt'
    comparison = True
    fmt = '{0} > {1}'


class LessEqual(BooleanOperationScheme):
    name = 'le'
    swapped = 'ge'
    comparison = True
    fmt = '{0} <= {1}'


class LessThan(BooleanOperationScheme):
    name = 'lt'
    swapped = 'gt'
    comparison = True
    fmt = '{0} < {1}'


class Contains(BooleanOperationScheme):
    name = 'contains'
    fmt = '{1} ∈ {0}'


class Negate(RequiresBooleanOperands, BooleanOperationScheme):
    name = 'neg'
    nargs = 1
    fmt = '!{0}'


class And(RequiresBooleanOperands, BooleanOperationScheme):
    name = 'and'
    commutative = True
    fmt = '{0} & {1}'


class Or(RequiresBooleanOperands, BooleanOperationScheme):
    name = 'or'
    commutative = True
    fmt = '{0} | {1}'


class ExclusiveOr(RequiresBooleanOperands, BooleanOperationScheme):
    name = 'xor'
    commutative = True
    fmt = '{0} xor {1}'
