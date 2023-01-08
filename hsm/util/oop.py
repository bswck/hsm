"""
Object-oriented programming hacks.

This module includes recipes, such as:
* factory constructor (never create distinct instances parametrized identically),
* smart initializer (initializer that works once per instance),
* idempotent allocator (makes Class(Class(...)) always equivalent to Class(...)).

They are useful to reduce memory usage dependingly on little costly runtime checks.
"""
import collections.abc
import functools
import threading
import types
import weakref
from typing import Any, Callable

FC_MEMO_ATTR = '__factory_constructor_memo__'
INITIALIZED_ATTR = '__initialized__'


# Inspired by factory constructors specially supported by Dart
# https://dart.dev/guides/language/language-tour#factory-constructors
def make_factory_constructor(
        make_key=lambda *args, **kwargs: args,
        new=None,
        pass_args=None,
):
    """
    Make a factory-constructor-based allocator that bases on provided make_key function
    that must return a hashable object.

    :param:`new` is used for allocating the object, defaults to object.__new__().
    :param:`pass_args` specifies whether to pass arguments to the constructor. Defaults to
    False if :param:`new` is None, otherwise True.

    By default, the :param:`make_key` function returns the *args tuple of the constructor call.
    If the args passed aren't hashable, an assertion error is raised in the debug mode.

    Usage:

    class Point2D:
        __new__ = make_factory_constructor()

        def __init__(self, x, y, /):
            self.x = x
            self.y = y

    p1 = Point2D(0, 0)
    p2 = Point2D(0, 0)
    setattr(p1, '__special_mark__', None)

    # p1 is always p2 (they occupy the same place in memory).
    assert p1 is p2
    assert hasattr(p2, '__special_mark__')

    del p1, p2

    p3 = Point2D(0, 0)

    # p3 is not p1 or p2 (those that were deleted).
    assert not hasattr(p3, '__special_mark__')
    """
    mutex = threading.RLock()

    if new is None:
        new = object.__new__
        if pass_args is None:
            pass_args = False
    pass_args = pass_args in (None, True)

    def __new__(cls, *args, **kwargs):
        memo = getattr(cls, FC_MEMO_ATTR, None)
        if memo is None:
            memo = weakref.WeakValueDictionary()
            setattr(cls, FC_MEMO_ATTR, memo)
        instance_key = make_key(*args, **kwargs)
        with mutex:
            assert isinstance(instance_key, collections.abc.Hashable)
            try:
                instance = memo[instance_key]
            except KeyError:
                instance = new(cls, *args, **kwargs) if pass_args else new(cls)
                memo[instance_key] = instance
        return instance

    return __new__


def factory_constructor(new=None, *, make_key=lambda *args, **kwargs: args):
    """
    Factory constructor decorator for convenience.

    Usage:

    class MyClass:
        @factory_constructor
        def __new__(cls, *args, **kwargs):
            ...
    """
    if new is None:
        return functools.partial(make_key=make_key)
    return make_factory_constructor(new=new, make_key=make_key)


class MissingT:
    """
    Marks a missing object.
    Singleton.
    """
    __new__ = make_factory_constructor()


MISSING = MissingT()


def smart_initializer(init=None):
    """
    Usage:

    class Foo:
        @smart_initializer
        def __init__(self, bar):
            self.bar = bar

    Makes initializers work only once per instance.

    foo = Foo(1)  # self.bar = 1
    foo.__init__(2)  # self.bar is still 1

    Note for advanced: to call the original constructor, use __init__.__wrapped__(cls, ...).
    """

    if init is None:
        init = object.__init__

    @functools.wraps(init)
    def __init__(self, *args, **kwargs):
        if getattr(self, INITIALIZED_ATTR, False):
            return
        init(self, *args, **kwargs)
        # allow errors to break the call, set initialized to True after successful initialization
        setattr(self, INITIALIZED_ATTR, True)

    return __init__


def idempotent(new=None):
    """
    Idempotent allocator. Recommended to be used with smart initializer.

    Usage:

    class WrappedInt:
        __new__ = idempotent()

        @smart_initializer
        def __init__(self, i: int):
            self.i = i

    wrapped_int = WrappedInt(1)
    wrapped_wrapped_int = WrappedInt(wrapped_int)

    # Idempotent allocation makes Class(...) and Class(Class(...)) mean the same thing.
    # Smart initializer prevents the ready instance from unintended reinitialization.
    assert wrapped_int is wrapped_wrapped_int

    # Combine with factory constructor

    class FWrappedInt:
        __new__ = idempotent(make_factory_constructor())

        @smart_initializer
        def __init__(self, i: int):
            self.i = i

    f_wrapped_int = WrappedInt(1)
    f_wrapped_int_2 = WrappedInt(1)
    f_wrapped_wrapped_int = WrappedInt(wrapped_int)

    assert f_wrapped_int is f_wrapped_int_2 is f_wrapped_wrapped_int
    """
    pass_args = True
    if new is None:
        new = object.__new__
        pass_args = False

    def __new__(cls, determinant=None, /, *args, **kwargs):
        if not isinstance(determinant, cls):
            return new(cls, determinant, *args, **kwargs) if pass_args else new(cls)
        return determinant
    return __new__


def marker(
        attribute: str,
        value: Any = MISSING,
        callback: Callable[[type | types.FunctionType, str, Any], None] = setattr
):
    """
    Shorthand for creating simple decorators.

    Examples
    --------
    Own version of abc.abstractmethod
        abstract = marker('__isabstractmethod__', True)

        @abstract
        def my_func():
            pass

    Average counter
        class MyClass:
            average_cost = 0

        cost = marker(
            'average', lambda _, attr, cost: setattr(
                MyClass, attr, (getattr(MyClass, attr)+cost)/2)
            )
        )

        @cost(1)
        class Subclass1:
            ...

        @cost(3)
        class Subclass2:
            ...

        assert MyClass.average_cost == 2
    """

    def decorator(runtime_value):
        def wrapper(cls):
            callback(cls, attribute, runtime_value)
        return wrapper

    if value is not MISSING:
        return decorator(value)

    return decorator


if __name__ == '__main__':
    class Point2D:
        __new__ = make_factory_constructor()

        def __init__(self, x, y, /):
            self.x = x
            self.y = y

    p1 = Point2D(0, 0)
    p2 = Point2D(0, 0)
    setattr(p1, '__special_mark__', None)

    # p1 is always p2 (they occupy the same place in memory).
    assert p1 is p2
    assert hasattr(p2, '__special_mark__')

    old_id = id(p1)  # or id(p2), does not matter
    del p1, p2

    p3 = Point2D(0, 0)

    # p3 is not p1 (p1 and p2 were deleted).
    assert not hasattr(p3, '__special_mark__')
