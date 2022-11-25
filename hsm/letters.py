from hsm._autoclasses import AutoClass, Parameter


class Letter(AutoClass):
    name: str = Parameter(default='x', factory_key=True)

    def __repr__(self):
        return self.name


def letters(name_string):
    if name_string.isalpha():
        names = name_string
    else:
        names = name_string.replace(' ', ',').split(',')
    return tuple(map(Letter, names))


_ = 'abcdefghijklmnopqrstuvwxyz'
a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z = letters(_)
