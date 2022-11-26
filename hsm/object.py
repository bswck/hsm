import functools
from hsm.toolkit import Namespace, Coercion, hint_coercion


@functools.singledispatch
def objects(value):
    raise ValueError(f'value {value!r} could not be recognised as a mathematical object')


class Object:
    from_value = staticmethod(objects)
    const = False

    def _get_value(self, context):
        raise NotImplementedError

    def get_value(self, context=None):
        return self._get_value(context or Context())


hint_coercion.register(Object, lambda tp: Coercion(tp, cast=objects))


@objects.register(Object)
def identity(obj):
    return obj


class Context(Namespace):
    pass

