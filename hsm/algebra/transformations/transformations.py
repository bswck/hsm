"""Transform algebraic operations."""
from __future__ import annotations

from typing import ClassVar

from hsm.algebra import operations


__all__ = (
    'Transformation',
    'BranchedTransformation',
)


class Transformation:
    wrapped: Transformation | operations.ExpressionOperand
    name: ClassVar[str | None] = None
    long_name: ClassVar[str | None] = None

    _classes = {}

    def __init_subclass__(cls, **kwargs):
        if not isinstance(cls.name, str) or not cls.name:
            return
        if not cls.long_name:
            cls.long_name = cls.name
        cls._classes[cls.name] = cls

    def check(self):
        raise NotImplementedError

    @classmethod
    def subtransform(cls, expression):
        return cls(expression)


class BranchedTransformation(Transformation):
    def transform(self):
        if self.wrapped.is_A:
            return self.transform_A()
        if self.wrapped.is_O:
            return self.transform_O()
        if self.wrapped.is_CO:
            return self.transform_CO()

    def transform_A(self):
        raise NotImplementedError

    def transform_O(self):
        raise NotImplementedError

    def transform_CO(self):
        raise NotImplementedError


class Simplify(BranchedTransformation):
    """
    Simplify the expression by summing all groups of similar monomials.

    It is not done 'on the fly', but it is a previously eagerly-computed expression
    in the background of the wrapped expression.
    """
