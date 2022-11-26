import decimal

from hsm.lib import Object, as_object
from hsm.toolkit import Dataclass, Parameter


@as_object.register(int)
@as_object.register(float)
@as_object.register(complex)
@as_object.register(decimal.Decimal)
class Const(Dataclass, Object):
    value = Parameter(factory_key=True)

    def _get_value(self, context):
        return self.value

    def __repr__(self):
        return str(self.value)
