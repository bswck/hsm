import decimal

from hsm.core import Object, as_object
from hsm.toolkit import Dataclass, Parameter


@as_object.register(int)
@as_object.register(float)
@as_object.register(decimal.Decimal)
class Const(Dataclass, Object):
    value: int | float | decimal.Decimal = Parameter(
        factory_key=True, allow_hint_coercions=False
    )

    def _get_value(self, context):
        return self.value

    def __hash__(self):
        # Since .value is hashable and every value of same hash produces same instance,
        # all objects Const(v) for the equal v are the same instance.
        # Thus, we can use ID of the instance as a relevant value-dependent hash of the instance.
        return id(self)

    def __repr__(self):
        repr_string = str(self.value)
        if self.value < 0:
            repr_string = repr_string.join('()')
        return repr_string

    def __neg__(self):
        return Const(-self.value)
