import functools
import weakref
from typing import ClassVar

from hsm.toolkit import Dataclass


class Operation(Dataclass):
    name: str | None = None
    full_name: ClassVar[str | None] = None
    min_args: ClassVar[int | None] = None
    max_args: ClassVar[int | float | None] = None
    priority: ClassVar[int] = 0
    associative: ClassVar[bool | None] = False
    commutative: ClassVar[bool] = False
    comparison: ClassVar[bool] = False
    chainable: ClassVar[bool | None] = None
    swapped: ClassVar[str | None] = None
    evaluates_to_bool: ClassVar[bool] = False
    _swapped_cls: 'ClassVar[type[Operation] | None]' = None

    _all_ops = {}
    _instances = weakref.WeakValueDictionary()

    def __new__(cls, name):
        if isinstance(name, cls):
            return name
        try:
            arith = cls._instances[name]
        except KeyError:
            arith = cls._all_ops[name]()
            cls._instances[name] = arith
        return arith

    def validate_operands(self, operation, operands, allowed_types):
        nargs = len(operands)
        if self.min_args is not None:
            min_args = self.min_args
            max_args = self.max_args
            if nargs < min_args:
                raise ValueError(
                    f'too few arguments for {self.full_name} '
                    f'(expected at least {min_args}, got {nargs})'
                )
            if nargs > max_args:
                if not self.chainable:
                    raise ValueError(
                        f'{self.full_name} operation is not chainable '
                        f'(too many arguments passed, maximally {max_args} accepted)'
                    )
                operation.chained = True
        for operand in operands:
            if not isinstance(operand, allowed_types):
                raise TypeError(
                    f'invalid operand type for {type(operation).__name__} '
                    f'{self.name}: {type(operand).__name__!r}'
                )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if isinstance(cls.name, str) and cls.name:
            cls.__ignore_missing_args__ = True
            cls.__new__ = functools.update_wrapper(lambda c: object.__new__(c), cls.__new__)
            cls._all_ops[cls.name] = cls
            swapped_name = cls.swapped
            swapped_cls = cls._swapped_cls
            if swapped_cls:
                cls.swapped = swapped_cls.name
                swapped_cls._swapped_cls = cls
            elif swapped_name:
                swapped_cls = cls._all_ops.get(swapped_name)
                if swapped_cls:
                    swapped_cls.swapped_name = cls.name
                    swapped_cls.swapped_cls = cls
                cls._swapped_cls = swapped_cls
            if cls.chainable is None:
                if cls.min_args is None:
                    cls.chainable = False
                else:
                    cls.chainable = cls.min_args > 1
            if cls.max_args is None:
                cls.max_args = float('inf')
            if not cls.full_name:
                cls.full_name = cls.name
#
#
# class Domain(Dataclass):
#     _all_domains = {}
#     _instances = weakref.WeakValueDictionary()
#
#     name = Argument()
#
#     def __new__(cls, name):
#         # Analogical behaviour to Arithmetic() constructor
#         if isinstance(name, cls):
#             return name
#         try:
#             domain = cls._instances[name]
#         except KeyError:
#             domain = cls._all_domains[name]()
#             cls._instances[name] = domain
#         return domain
