import math
from hsm.toolkit import Dataclass
from hsm.core import Object


class Logarithm(Dataclass, Object):
    x: Object
    a: Object = 10
    r: Object = 1

    def _get_value(self, context):
        return self.r * math.log(self.x, base=self.a)
