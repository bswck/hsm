import functools
from hsm.toolkit import Namespace, Coercion, hint_coercions


@functools.singledispatch
def recognition(value):
    raise ValueError(f'value {value!r} could not be recognised as a mathematical object')


class Object:
    from_value = staticmethod(recognition)
    const = False

    def _get_value(self, context):
        raise NotImplementedError

    def get_value(self, context=None):
        return self._get_value(context or Context())


hint_coercions.register(Object, Coercion(Object, cast=recognition))


@recognition.register(Object)
def identity(obj):
    return obj


class Context(Namespace):
    pass

