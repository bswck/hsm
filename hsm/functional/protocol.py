import functools

from hsm.toolkit import Dataclass, Parameter


class Metadata(Dataclass):
    repr: str
    _: Parameter.KW_ONLY
    symbols: list[str] = Parameter(default_factory=list)
    nargs: int = 2
    commutative: bool = False
    comparison: bool = False
    inverse: str | None = None
    chainable: bool = Parameter(
        default_factory=lambda self: self.nargs > 1,
        instance_factory=True
    )

    @property
    def all_kinds(self):
        return set(self.__constructor__.instances)


class Protocol:
    _all_protos = {}

    name = None
    metadata = None  # type: Metadata
    priority = -1
    swapped = None
    _swapped_cls = None

    @staticmethod
    def swap_operands(objects):
        return objects

    def swap(self, op, objects):
        if self._swapped_cls is None:
            raise ValueError(f'cannot swap {self.name} operation')
        return type(op)(self._swapped_cls, *self.swap_operands(objects))

    def repr(self, op, objects):
        repr_fmt = self.metadata.repr
        repr_string = repr_fmt.format(*objects)
        if op.chained:
            repr_string = functools.reduce(
                repr_fmt.format,
                objects[op.nargs::],
                repr_string
            )
        return repr_string

    def validate_args(self, op, objects):
        nargs = len(objects)
        if self.metadata.nargs != -1:
            if nargs < self.metadata.nargs:
                raise ValueError(
                    f'too few arguments for {self.name} '
                    f'(expected {self.metadata.nargs}, got {nargs})'
                )
            if nargs > self.metadata.nargs:
                if not self.metadata.chainable:
                    raise ValueError(
                        f'{self.name} operation is not chainable '
                        '(too many arguments passed)'
                    )
                op.chained = True

    def __init_subclass__(cls, **kwargs):
        cls._all_protos[cls.name] = cls
        swapped_name = cls.swapped
        swapped_cls = cls._swapped_cls
        if swapped_cls:
            cls.swapped = swapped_cls.name
            swapped_cls._swapped_cls = cls
        elif swapped_name:
            swapped_cls = cls._all_protos.get(swapped_name)
            if swapped_cls:
                swapped_cls.swapped_name = cls.name
            swapped_cls.swapped_cls = cls
            cls._swapped_cls = swapped_cls
