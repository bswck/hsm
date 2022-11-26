import decimal

from hsm.object import Object, objects
from hsm.toolkit import Dataclass, Parameter


@objects.register(int)
@objects.register(float)
@objects.register(complex)
@objects.register(decimal.Decimal)
class Const(Dataclass, Object):
    value = Parameter()

    def _get_value(self, context):
        return self.value
