import functools
import weakref
from typing import ClassVar

from hsm.toolkit import Dataclass, Argument


# To be invented later
class Domain(Dataclass):
    pass


class OperationScheme(Dataclass):
    _all_schemes = {}
    _instances = weakref.WeakValueDictionary()

    name = Argument()
    fmt: ClassVar[str] = '{0}?'
    nargs: ClassVar[int | None] = None
    priority: ClassVar[int] = -1
    associative: ClassVar[bool | None] = False
    commutative: ClassVar[bool] = False
    comparison: ClassVar[bool] = False
    inverse: ClassVar[str | None]
    chainable: ClassVar[bool | None] = None
    swapped: ClassVar[str | None] = None
    _swapped_cls: 'ClassVar[type[OperationScheme] | None]' = None

    def __new__(cls, name):
        try:
            scheme = cls._instances[name]
        except KeyError:
            scheme = cls._all_schemes[name](name)
            cls._instances[name] = scheme
        return scheme

    def validate_operands(self, operation, operands, allowed_types):
        nargs = len(operands)
        if self.nargs is not None:
            if self.nargs < 0:
                min_args = abs(self.nargs)
                max_args = float('inf')
            else:
                min_args = max_args = self.nargs

            if nargs < min_args:
                raise ValueError(
                    f'too few arguments for {self.name} '
                    f'(expected at least {min_args}, got {nargs})'
                )
            if nargs > max_args:
                if not self.chainable:
                    raise ValueError(
                        f'{self.name} operation is not chainable '
                        f'(too many arguments passed, maximally {max_args} accepted)'
                    )
                operation.chained = True
        for operand in operands:
            if not isinstance(operand, allowed_types):
                raise TypeError(
                    f'invalid operand type for {type(operation).__name__} '
                    f'{self.name}: {type(operand).__name__!r}'
                )

    @staticmethod
    def swap_operands(operands):
        return operands

    def swap(self, op, objects):
        if self._swapped_cls is None:
            raise ValueError(f'cannot swap {self.name} operation')
        return type(op)(self._swapped_cls, *self.swap_operands(objects))

    def repr(self, operation, objects, parentheses=False):
        fmt = self.fmt
        self_priority = self.priority
        repr_string = fmt.format(
            *(obj.repr(parentheses=self_priority > obj.priority) for obj in objects)
        )
        if operation.chained:
            repr_string = functools.reduce(
                fmt.format,
                (
                    obj.repr(parentheses=self_priority > obj.priority)
                    for obj in objects[operation.scheme.nargs::]
                ),
                repr_string
            )
        if parentheses:
            repr_string = repr_string.join('()')
        return repr_string

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__new__ = lambda c, name: object.__new__(c)
        cls._all_schemes[cls.name] = cls
        swapped_name = cls.swapped
        swapped_cls = cls._swapped_cls
        if swapped_cls:
            cls.swapped = swapped_cls.name
            swapped_cls._swapped_cls = cls
        elif swapped_name:
            swapped_cls = cls._all_schemes.get(swapped_name)
            if swapped_cls:
                swapped_cls.swapped_name = cls.name
                swapped_cls.swapped_cls = cls
            cls._swapped_cls = swapped_cls
        if cls.chainable is None:
            if cls.nargs is None:
                cls.chainable = False
            else:
                cls.chainable = cls.nargs > 1

    def __repr__(self):
        return self.name
