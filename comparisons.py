from hsm.toolkit import Dataclass, Arguments
from hsm.object import Object
from hsm.operations import Operation


class ChainedComparison(Dataclass):
    """
    Chained comparison of objects.

    ChainedComparison('LESS THAN', x, y, 5) -> x < y < 5
    ChainedComparison('<', x, y, 5) -> x < y < 5
    """

    comparator: Operation
    objects: list[Object] = Arguments()

    def __len__(self):
        return len(self.objects)
