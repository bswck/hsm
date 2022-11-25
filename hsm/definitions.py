from typing import Callable, Optional

from hsm.toolkit import Dataclass, Parameter, Arguments, Coercion


class Symbol(Dataclass):
    name: str = Parameter(default='x', factory_key=True)

    def __repr__(self):
        return self.name


def symbols(name_string):
    if name_string.isalpha():
        names = name_string
    else:
        names = name_string.replace(' ', ',').split(',')
    return tuple(map(Symbol, names))


_ = 'abcdefghijklmnopqrstuvwxyz'
a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z = symbols(_)


class Constraint(Dataclass):
    impl: Optional[Callable] = None
    description: str | None = Parameter(
        Coercion(None, str.strip),
        default_factory=lambda self: str(self.impl) if isinstance(self.impl, Definition) else None,
        instance_factory=True
    )

    def check(self, context):
        if not self.impl(context):
            description = ': ' + self.description if self.description else ''
            raise ValueError(f'constraint failed for {context}{description}')


class Definition(Dataclass):
    constraint: Constraint
    constraints: tuple[Constraint, ...] = Arguments()
