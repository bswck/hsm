import functools
import numbers
from typing import ClassVar

from hsm.toolkit import Dataclass, KeywordArguments

PARENTHESES = '()'
NO_PARENTHESES = '', ''


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

    def repr(self, arith, operation, operands, tree=False, parentheses=False, **kwds):
        try:
            subrepr = self.repr_dispatch[self.repr_type]
        except KeyError:
            raise ValueError(f'invalid representation type: {self.repr_type}')
        repr_string = subrepr(
            self, arith, operation, operands,
            tree=tree, **{**self.kwds, **kwds}
        )
        if tree or parentheses:
            repr_string = repr_string.join(PARENTHESES)
        return repr_string

    def __init_subclass__(cls, new_dispatch=True, **kwargs):
        super().__init_subclass__(**kwargs)
        if new_dispatch:
            cls.repr_dispatch = {}


class PythonReprEngine(ReprEngine):
    def repr_operand(
        self, arith, operand,
        operation, tree=False, parentheses=False,
        associativity_parenthesization=True,
        priority_parenthesization=True, context=None, **kwds
    ):
        return operand.repr(
            parentheses=not operand.is_A and (
                parentheses
                or tree
                or (
                    priority_parenthesization
                    and arith.priority >= operand.priority
                    and associativity_parenthesization
                    and (context or (context and arith is not operand.arith))
                    and not arith.associative
                )
            )
        )


def infix_operator(symbol, add_surrounding_spaces=True, **kwds):
    infix = symbol
    if add_surrounding_spaces:
        infix = ' ' + infix + ' '
    return PythonReprEngine(infix, 'join', **kwds)


class CompleteReprEngine(ReprEngine, new_dispatch=False):
    def repr_atomic(self, value, arith, operand, operation, parentheses=False, **kwds):
        raise NotImplementedError

    def repr_operand(self, arith, operand, operation, tree=False, parentheses=False, **kwds):
        if operand.is_A:
            return self.repr_atomic(
                operand.value,
                arith, operand,
                operation,
                parentheses=parentheses,
                **kwds
            )
        return self.repr(
            operand.arith, operand, operand.operands,
            parentheses=parentheses, **kwds
        )


@PythonReprEngine.repr_factory(name='composition')
def composition(engine, arith, operation, operands, **kwds):
    fmt = engine.repr_fmt
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
def join(engine, arith, operation, operands, **kwds):
    context = []
    return engine.repr_fmt.join(
        (
            engine.repr_operand(arith, operand, operation, context=context, **kwds),
            context.append(operand)
        )[0]
        for operand in operands
    )


@PythonReprEngine.repr_factory(name='list')
def list_(engine, arith, operation, operands, **kwds):
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
