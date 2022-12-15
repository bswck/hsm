import functools
import numbers
from typing import ClassVar

from hsm.toolkit import Dataclass, KeywordArguments

PARENTHESES = '()'
NO_PARENTHESES = '', ''


class ReprContext(Dataclass):
    neighbours: tuple


class ReprEngine(Dataclass):
    repr_fmt: str
    repr_type: str
    kwds: dict = KeywordArguments()

    repr_dispatch: ClassVar[dict]

    @classmethod
    def repr_factory(cls, fn=None, *, name):
        if fn is None:
            return functools.partial(cls.repr_factory, name=name)
        cls.repr_dispatch[name] = fn
        return fn

    def repr_operand(self, arith, operand, operation, parentheses=False, **kwds):
        raise NotImplementedError


class PythonReprEngine(ReprEngine):
    def repr_operand(
        self, arith, operand,
        operation, tree=False, parentheses=False,
        associativity_parenthesization=True,
        priority_parenthesization=True, context=None,
        **kwds
    ):
        if not operand.is_A:
            parentheses = (
                parentheses
                or tree
                or (
                    priority_parenthesization
                    and arith.priority >= operand.priority
                    and associativity_parenthesization
                    and context  # and ((not parentheses_require_context) or context)
                    and ((arith.priority > operand.priority) or not arith.associative)
                )
            )
            context = None
        return operand.repr(parentheses=parentheses, context=context)


def infix_operator(symbol, add_surrounding_spaces=True, **kwds):
    infix = symbol
    if add_surrounding_spaces:
        infix = ' ' + infix + ' '
    return PythonReprEngine(infix, 'join', **kwds)


class CompleteReprEngine(ReprEngine, new_dispatch=False):
    def repr_operand(self, arith, operand, operation, parentheses=False, **kwds):
        pass

    def repr_atomic(self, value, arith, operand, operation, parentheses=False, **kwds):
        raise NotImplementedError


@PythonReprEngine.repr_factory(name='composition')
def composition(engine, arith, operation, operands, context=None, **kwds):
    fmt = engine.repr_fmt
    if context is None:
        context = []
    repr_string = fmt.format(*(
        (
            engine.repr_operand(arith, operand, operation, context=context, **kwds),
            context.append(operand)
        )[0]
        for operand in operands[:operation.arith.min_args]
    ))
    if operation.chained:
        repr_string = functools.reduce(
            fmt.format,
            (
                (
                    engine.repr_operand(arith, operand, operation, context=context, **kwds),
                    context.append(operand)
                )[0]
                for operand in operands[operation.arith.min_args:]
            ),
            repr_string
        )
    return repr_string


@PythonReprEngine.repr_factory(name='join')
def join(engine, arith, operation, operands, context=None, **kwds):
    if context is None:
        context = []
    return engine.repr_fmt.join(
        (
            engine.repr_operand(arith, operand, operation, context=context, **kwds),
            context.append(operand)
        )[0]
        for operand in operands
    )


@PythonReprEngine.repr_factory(name='list')
def list_(engine, arith, operation, operands, context=None, **kwds):
    if context is None:
        context = []
    return engine.repr_fmt.format(
        engine.listing_denominator.join(
            (
                engine.repr_operand(arith, operand, operation, context=context, **kwds),
                context.append(operand)
            )[0]
            for operand in operands
        )
    )


class LatexReprEngine(CompleteReprEngine):
    @functools.singledispatchmethod
    def repr_atomic(self, value, arith, operand, operation, parentheses=False, **kwds):
        raise ValueError(f'cannot latexify value of type {type(value).__name__}')

    @repr_atomic.register(numbers.Real)
    def repr_number(self, value, *_args, **_kwargs):
        return str(value)
