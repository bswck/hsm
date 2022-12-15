import functools
import weakref
from typing import ClassVar

from hsm.toolkit import Dataclass, Argument


class Arithmetic(Dataclass):
    _all_ariths = {}
    _instances = weakref.WeakValueDictionary()

    name = Argument()
    min_args: ClassVar[int | None] = None
    max_args: ClassVar[int | float | None] = None
    priority: ClassVar[int] = 0
    associative: ClassVar[bool | None] = False
    commutative: ClassVar[bool] = False
    comparison: ClassVar[bool] = False
    chainable: ClassVar[bool | None] = None
    swapped: ClassVar[str | None] = None
    evaluates_to_bool: ClassVar[bool] = False
    _swapped_cls: 'ClassVar[type[Arithmetic] | None]' = None

    def __new__(cls, name):
        if isinstance(name, cls):
            return name
        try:
            arith = cls._instances[name]
        except KeyError:
            arith = cls._all_ariths[name]()
            cls._instances[name] = arith
        return arith

    def validate_operands(self, operation, operands, allowed_types):
        nargs = len(operands)
        if self.min_args is not None:
            min_args = self.min_args
            max_args = self.max_args
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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.name:
            cls.__ignore_missing_args__ = True
            cls.__new__ = functools.update_wrapper(lambda c: object.__new__(c), cls.__new__)
            cls._all_ariths[cls.name] = cls
            swapped_name = cls.swapped
            swapped_cls = cls._swapped_cls
            if swapped_cls:
                cls.swapped = swapped_cls.name
                swapped_cls._swapped_cls = cls
            elif swapped_name:
                swapped_cls = cls._all_ariths.get(swapped_name)
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