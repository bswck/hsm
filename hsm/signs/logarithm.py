import math
from hsm.toolkit import Dataclass
from hsm.arith.tree import AtomicNode


class Logarithm(Dataclass, AtomicNode):
    x: AtomicNode
    a: AtomicNode = 10
    r: AtomicNode = 1

    def _get_value(self, context):
        return self.r * math.log(self.x, base=self.a)
