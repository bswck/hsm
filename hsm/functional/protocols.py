from hsm.functional.protocol import Protocol, Metadata


class Operations:
    MATMUL = matmul = Metadata('{0} @ {1}')
    CONTAINS = contains = Metadata('{1} ∈ {0}')
    GET = get = Metadata('{1}[{0}]')

    ABS = abs = Metadata('|{0}|', nargs=1)
    INVERT = invert = Metadata('~{0}', nargs=1)


class Addition(Protocol):
    name = 'add'
    priority = 0
    metadata = Metadata('{0} + {1}', commutative=True)


class Subtraction(Addition):
    name = 'sub'
    metadata = Metadata('{0} - {1}')


class Multiplication(Protocol):
    name = 'mul'
    priority = Addition.priority + 1
    metadata = Metadata('{0}*{1}', commutative=True)


class Division(Multiplication):
    name = 'div'
    metadata = Metadata('{0}/{1}')


class Power(Protocol):
    name = 'pow'
    priority = Multiplication.priority + 1
    metadata = Metadata('{0}^{1}', chainable=False)  # chainable=1 is semantically ambiguous here.


class Root(Power):
    name = 'root'
    metadata = Metadata('{0}^(1/{1})', chainable=False)


class FormulaProtocol(Protocol):
    priority = float('inf')


class Equal(FormulaProtocol):
    name = 'eq'
    metadata = Metadata('{0} == {1}', commutative=True, comparison=True)


class Inequal(FormulaProtocol):
    name = 'ne'
    metadata = Metadata('{0} != {1}', commutative=True, comparison=True)


class GreaterEqual(FormulaProtocol):
    name = 'ge'
    swapped = 'le'
    metadata = Metadata('{0} >= {1}', comparison=True)


class GreaterThan(FormulaProtocol):
    name = 'gt'
    swapped = 'lt'
    metadata = Metadata('{0} > {1}', comparison=True)


class LessEqual(FormulaProtocol):
    name = 'le'
    swapped = 'ge'
    metadata = Metadata('{0} <= {1}', comparison=True)


class LessThan(FormulaProtocol):
    name = 'lt'
    swapped = 'gt'
    metadata = Metadata('{0} < {1}', comparison=True)


class And(FormulaProtocol):
    name = 'and'
    metadata = Metadata('{0} & {1}', commutative=True)


class Or(FormulaProtocol):
    name = 'or'
    metadata = Metadata('{0} | {1}', commutative=True)


class XOr(FormulaProtocol):
    metadata = Metadata('{0} xor {1}', commutative=True)
