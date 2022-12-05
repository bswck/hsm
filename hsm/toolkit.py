import collections
import functools
import inspect
import itertools
import keyword
import operator
import re
import types
import typing
import weakref

from hsm.errors import CoercionError
from hsm.errors import ConstructorError

if __debug__:
    class _DataclassMeta(type):
        __constructor__: 'Constructor'

        def __repr__(self):
            constructor = self.__constructor__
            if constructor:
                return f'<class {self.__qualname__}{constructor!r}>'
            return type.__repr__(self)

else:
    _DataclassMeta = type  # noqa


class Dataclass(metaclass=_DataclassMeta):
    __constructor__ = None
    __constructor_scan_annotations__ = True
    __constructor_kwargs__ = {}
    __constructor_factory_key__ = None

    def __new__(cls, *args, **kwargs):
        constructor = cls.__constructor__
        if constructor:
            return constructor.new(cls, args, kwargs)
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        constructor = self.__constructor__
        if constructor:
            constructor.init(self, args, kwargs)
            constructor.post_init(self)
        elif args or kwargs:
            raise TypeError(f'{type(self).__name__}() takes no arguments')

    def __init_subclass__(cls, generate_constructor=True, factory_key=None):
        if factory_key:
            cls.__constructor_factory_key__ = factory_key
        if generate_constructor:
            constructor = generate_dataclass_constructor(cls)
            factory_key = cls.__constructor_factory_key__
            if constructor and factory_key:
                constructor.factory_key = factory_key

    if __debug__:
        def __repr__(self):
            constructor = self.__constructor__
            if constructor:
                return type(self).__qualname__ + ', '.join(
                    f'{name!s}={getattr(self, name)!r}' for name in constructor.attributes
                ).join('()')
            return object.__repr__(self)


class _Sentinel:
    def __bool__(self):
        return False

    if __debug__:
        def __repr__(self):
            return f'<sentinel>'


MISSING = _Sentinel()
INFINITE = float('inf')


class CoercionBase:
    pass


class Coercion(CoercionBase):
    """Simple single-value coercion."""

    def __init__(
        self,
        data_type=None,
        pre_conversion=None,
        post_conversion=None,
        cast=MISSING,
    ):
        if not isinstance(data_type, type):
            pre_conversion = data_type
            data_type = None
        self.data_type = data_type
        self.pre_conversion = pre_conversion
        self.post_conversion = post_conversion
        if cast is MISSING:
            cast = self.data_type
        self.cast = cast

        self.__no_cast = None

    @staticmethod
    def _coerce(callee, value, name=None):
        """Call object coercer and ensure to include additional failure context, if provided."""

        if callable(callee):
            try:
                valid = callee(value)
            except CoercionError as failure:
                failure.param = name
                raise failure from None
            return valid
        return value

    def with_cast(self, cast):
        if cast is None:
            cached = self.__no_cast
            if cached:
                if (
                    self.data_type is cached.data_type
                    and self.pre_conversion is cached.pre_conversion
                    and self.post_conversion is cached.post_conversion
                    and cached.cast is None
                ):
                    return cached
            if self.cast is None:
                self.__no_cast = self
            else:
                self.__no_cast = type(self)(
                    data_type=self.data_type,
                    pre_conversion=self.pre_conversion,
                    cast=None,
                    post_conversion=self.post_conversion
                )
            return self.__no_cast
        return type(self)(
            data_type=self.data_type,
            pre_conversion=self.pre_conversion,
            cast=cast,
            post_conversion=self.post_conversion
        )

    def coerce(self, value, name=None):
        """Try to coerce a valid value for construction."""

        data_type = self.data_type
        pre_convert = self.pre_conversion
        post_convert = self.post_conversion

        # Expected data type is provided, examine the value with reference to it.
        if data_type is not None:
            if isinstance(value, data_type):
                # Value is of the proper data type.
                obj = value
            else:
                # Need to cast the value to the proper data type.
                # Validate before trying, then cast, and let the errors propagate if any.
                value = self._coerce(pre_convert, value, name=name)
                if callable(self.cast):
                    try:
                        obj = self.cast(value)
                    except Exception as exc:
                        raise CoercionError(
                            f'could not cast {type(value).__name__} {value!r} '
                            f'to {data_type.__name__}',
                            param=name
                        ) from exc
                else:
                    obj = value
        # Expected data type is not provided, we assume the value is of an acceptable data type.
        else:
            obj = value

        # Validate the object of an acceptable data type.
        obj = self._coerce(post_convert, obj, name=name)
        return obj

    if __debug__:
        def __repr__(self):
            repr_string = f'<%s{type(self).__name__}%s>'
            repr_chunks = []
            if self.data_type:
                repr_chunks.append(f'type={self.data_type.__name__}')
            if self.pre_conversion and self.pre_conversion is not self.data_type:
                repr_chunks.append(f'before_cast={self.pre_conversion}')
            if self.cast is not self.data_type:
                repr_chunks.append(f'cast={self.cast}')
            if self.post_conversion:
                repr_chunks.append(f'after_cast={self.post_conversion}')
            if not repr_chunks:
                return repr_string % ('Null', '')
            return repr_string % ('', ' ' + ' '.join(repr_chunks))


class RecursiveCoercion(CoercionBase):
    class _LazyCollectionCoercion:
        def __init__(self, coercion, iterable, depth, name=None):
            self.coercion = coercion
            self.iterator = iter(iterable)
            self.depth = depth
            self.name = name

        def __next__(self):
            next_obj = next(self.iterator)
            return self.coercion.coerce(
                next_obj,
                depth=self.depth,
                name=self.name
            )

    def __init__(
        self,
        result_coercion=None,
        element_coercion=None,
        lazy=False,
        recursion_depth=0,
        iterable_types=typing.Iterable
    ):
        self.result_coercion = result_coercion
        self.element_coercion = element_coercion
        self.iterable_types = iterable_types
        self.recursion_depth = recursion_depth
        self.lazy = lazy

    def with_cast(self, cast):
        result_coercion = self.result_coercion
        if result_coercion:
            result_coercion = result_coercion.with_cast(cast)

        element_coercion = self.element_coercion
        if element_coercion:
            element_coercion = element_coercion.with_cast(cast)

        if result_coercion is self.result_coercion and element_coercion is self.element_coercion:
            return self

        return type(self)(
            result_coercion=result_coercion,
            element_coercion=element_coercion,
            lazy=self.lazy,
            recursion_depth=self.recursion_depth,
            iterable_types=self.iterable_types
        )

    def coerce(self, value, depth=0, name=None):
        if isinstance(value, self.iterable_types):
            if 0 <= depth <= self.recursion_depth:
                if self.lazy:
                    return self._LazyCollectionCoercion(self, value, depth+1, name=name)
                valid_elems = []
                for elem in value:
                    valid_elems.append(self.coerce(elem, depth+1, name=name))
                return self.result_coercion.coerce(valid_elems, name=name)
        if depth > self.recursion_depth:
            return self.element_coercion.coerce(value, name=name)
        return self.result_coercion.coerce(value, name=name)

    if __debug__:
        def __repr__(self):
            result = self.result_coercion
            elements = self.element_coercion
            depth = self.recursion_depth
            lazy = self.lazy
            return (
                f'<{"lazy " if lazy else ""}'
                f'{type(self).__name__} {result=} {elements=} {depth=}>'
            )


class SelectCoercion(CoercionBase):
    EXCEPTIONS = (Exception,)

    def __init__(self, *coercions):
        self.coercions = coercions

    def with_cast(self, cast):
        coercions = [coercion.with_cast(cast) for coercion in self.coercions]
        if all(map(operator.is_, self.coercions, coercions)):
            return self
        return type(self)(*coercions)

    def coerce(self, value, name=None):
        valid = MISSING
        for coercion in self.coercions[::-1]:
            try:
                valid = coercion.coerce(value, name=name)
            except self.EXCEPTIONS:
                pass
            if valid is not MISSING:
                return valid
        raise CoercionError(f'value {value} any of coercions {self}')

    if __debug__:
        def __repr__(self):
            return ' | '.join(map(repr, self.coercions))


identity = Coercion()


class Parameter:
    KW_ONLY = _Sentinel()

    POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
    POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
    VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
    KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
    VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD

    def __init__(
        self,
        *coercions,
        default=MISSING,
        default_factory=None,
        cast=MISSING,
        instance_factory=False,
        allow_hint_coercions=True,
        attribute=MISSING,
        kind=POSITIONAL_OR_KEYWORD,
        factory_key=False,
    ):
        self.default = default
        self.default_factory = default_factory
        self.instance_factory = instance_factory
        self.attribute = attribute
        self.allow_hint_coercions = allow_hint_coercions
        self.is_factory_key = factory_key
        self.cast = cast

        self.coercions = []
        self.coercions[:] = map(self.map_coercion, coercions)

        self.kind = kind

        self._from_attribute = None

    ERROR = _Sentinel()

    def map_coercion(self, coercion):
        if self.cast is not MISSING:
            coercion = coercion.with_cast(self.cast)
        return coercion

    def add_coercion(self, coercion, location='f', _is_hint_coercion=False):
        if _is_hint_coercion and not self.allow_hint_coercions:
            return
        coercion = self.map_coercion(coercion)
        if 'f' in location:
            self.coercions.insert(0, coercion)
        if 'b' in location:
            self.coercions.append(coercion)

    def remove_coercion(self, coercion):
        coercion = self.map_coercion(coercion)
        while coercion in self.coercions:
            self.coercions.remove(coercion)

    def set(self, name, context, instance=None, value=MISSING):
        if value is MISSING:
            default = self.default
            if default is MISSING:
                default_factory = self.default_factory
                if callable(default_factory):
                    if self.instance_factory:
                        value = default_factory(instance)
                    else:
                        value = default_factory()
                else:
                    if self.kind == self.VAR_POSITIONAL:
                        value = ()
                    elif self.kind == self.VAR_KEYWORD:
                        value = {}
                    else:
                        context.missing.reassembled_to_addition(name)
                        return self.ERROR
            else:
                value = default
        obj = functools.reduce(
            lambda cur_value, cur_coercion:
            cur_coercion.coerce(cur_value, name=name),
            self.coercions, value
        )
        if instance is not None:
            attribute = self.attribute
            if attribute is MISSING:
                attribute = name
            if isinstance(attribute, str):
                setattr(instance, attribute, obj)
            # elif (
            #     self._from_attribute
            #     and isinstance(getattr(instance, self._from_attribute, None), type(self))
            # ):
            #     delattr(instance, self._from_attribute)
        return obj

    def _inspect(self, name):
        self._from_attribute = name
        default = {}
        if self.kind not in (self.VAR_POSITIONAL, self.VAR_KEYWORD):
            default.update(default=self.default)
        return inspect.Parameter(
            name=name,
            kind=self.kind,
            **default
        )

    VAR_POS_PREFIX = '*'
    VAR_KW_PREFIX = '**'
    DEFAULT_JOIN = '='
    DEFAULT_FAC_JOIN = '->'
    DEFAULT_FACINST_JOIN = '~>'
    UNNAMED = '(param?)'

    PAT = re.compile(
        rf'(?P<variadic_prefix>{re.escape(VAR_POS_PREFIX)}|{re.escape(VAR_KW_PREFIX)})'
        rf'(?P<name>\S+)((?P<join>{DEFAULT_JOIN}|{DEFAULT_FAC_JOIN}|{DEFAULT_FACINST_JOIN})'
        rf'(?P<default>.*))?'
    )

    @classmethod
    def from_str(cls, string, *coercions, default_parse=eval):
        inst = cls(*coercions)
        match = cls.PAT.match(string)
        if match:
            data = match.groupdict()
            variadic_prefix = data['variadic_prefix']
            name = data['name']
            default = data.get('default', MISSING)
            default_is_factory = data.get('join') in (cls.DEFAULT_JOIN, cls.DEFAULT_FACINST_JOIN)
            if default_is_factory:
                inst.instance_factory = data.get('join') == cls.DEFAULT_FACINST_JOIN
            if variadic_prefix == cls.VAR_POS_PREFIX:
                inst.kind = cls.VAR_POSITIONAL
            if variadic_prefix == cls.VAR_POS_PREFIX:
                inst.kind = cls.VAR_KEYWORD
            if keyword.iskeyword(name) or name.isidentifier():
                raise ValueError('parameter name must be an identifier')
            if default:
                default_obj = default_parse(default)
                if default_is_factory:
                    inst.default_factory = default_obj
                else:
                    inst.default = default_obj
        else:
            raise ValueError('parameter string did not match')
        return inst

    def repr(self, name=None):
        repr_string = name or self.UNNAMED
        if self.kind in (self.VAR_POSITIONAL, self.VAR_KEYWORD):
            if self.kind == self.VAR_POSITIONAL:
                repr_string = self.VAR_POS_PREFIX + repr_string
            elif self.kind == self.VAR_KEYWORD:
                repr_string = self.VAR_KW_PREFIX + repr_string
        default_obj = self.default or self.default_factory
        const = default_obj is self.default
        if default_obj:
            join = (
                (self.DEFAULT_FAC_JOIN, self.DEFAULT_FACINST_JOIN)[self.instance_factory],
                self.DEFAULT_JOIN
            )[const]
            repr_string += join
            obj = getattr(
                self.default_factory if self.default_factory else self.default,
                '__name__',
                None
            )
            if self.default_factory and obj:
                obj += '()'
            if obj:
                repr_string += obj
            else:
                if self.default_factory:
                    chunk = repr(self.default_factory).join('()')
                else:
                    chunk = repr(self.default)
                repr_string += chunk
        return repr_string

    if __debug__:
        def __repr__(self):
            return self.repr(name=self._from_attribute or 'argument')


Argument = functools.partial(Parameter, kind=Parameter.POSITIONAL_ONLY)
Arguments = functools.partial(Parameter, kind=Parameter.VAR_POSITIONAL)
KeywordArgument = functools.partial(Parameter, kind=Parameter.KEYWORD_ONLY)
KeywordArguments = functools.partial(Parameter, kind=Parameter.VAR_KEYWORD)


class _AttributialItemOps:
    def __setattr__(self, key, value):
        data = self
        if key in data:
            data[key] = value
        else:
            object.__setattr__(self, key, value)

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            try:
                return object.__getattribute__(self, item)
            except AttributeError:
                raise AttributeError(f'{type(self).__name__}.{item}') from None


class Namespace(dict, _AttributialItemOps):
    pass


class Constructor(collections.UserDict, _AttributialItemOps):
    factory_key = None
    INITIALIZED_FLAG = '__hsm_initialized__'

    def __init__(self, other=None, /, **kwargs):
        super().__init__(other)
        if not hasattr(self, 'instances'):
            self.instances = weakref.WeakValueDictionary()
        if kwargs:
            self.update(kwargs)
        self.initialized = weakref.WeakSet()
        self.signature = None
        self.validate_parameters()

    def mark_initialized(self, instance):
        setattr(instance, self.INITIALIZED_FLAG, True)

    def is_initialized(self, instance):
        return getattr(instance, self.INITIALIZED_FLAG, False)

    def validate_parameters(self):
        parameters = list(itertools.starmap(
            lambda name, param: param._inspect(name),
            self.data.items()
        ))
        self.signature = inspect.Signature(parameters=parameters)

    def __new__(cls, constructor=None, /, **kwargs):
        if constructor and isinstance(constructor, cls):
            return constructor
        return object.__new__(cls)

    def __setattr__(self, key, value):
        try:
            data = object.__getattribute__(self, 'data')
        except AttributeError:
            set_attr = True
        else:
            set_attr = False
            if key in data:
                data[key] = value
            else:
                set_attr = True
        if set_attr:
            object.__setattr__(self, key, value)

    @classmethod
    def factory(cls, key_maker):
        constructor = cls()
        constructor.factory_key = key_maker
        return constructor

    def new(self, cls, args, kwargs):
        key_maker = self.factory_key
        key = MISSING

        if key_maker:
            if callable(key_maker):
                key = key_maker()
            elif isinstance(key_maker, (str, tuple)):
                if isinstance(key_maker, str):
                    arguments = key_maker.replace(' ', ',').split(',')
                else:
                    arguments = key_maker
                # Unfortunately we cannot use ._bind() since it is private,
                # thus it's needed to iter over args and kwargs again and again. :(
                bound = self.signature.bind(*args, **kwargs).arguments
                missing = set()
                key = []
                for argument in arguments:
                    parameter = self.parameters[argument]
                    try:
                        specified_value = bound[argument]
                    except KeyError:
                        if (
                            parameter.default is MISSING
                            and parameter.default_factory
                            and parameter.instance_factory
                        ):
                            raise ValueError(
                                'constructor factory key parameter cannot take instance'
                                'as an argument, because it can be not created yet'
                            ) from None
                        value = parameter.set(argument, Namespace(missing=missing))
                        if value is not MISSING:
                            key.append(value)
                    else:
                        value = parameter.set(
                            argument,
                            Namespace(missing=missing),
                            value=specified_value
                        )
                        key.append(value)
                if missing:
                    raise TypeError(
                        f'{cls.__name__}.__new__() missing {len(missing)} '
                        f'required argument(s): {", ".join(missing)}'
                    ) from None
                key = tuple(key)

            if key is MISSING:
                raise ConstructorError('invalid key maker for factory constructor')

            try:
                return self.instances[key]
            except KeyError:
                temporary_reference = object.__new__(cls)
                self.instances[key] = temporary_reference
                return temporary_reference

        return object.__new__(cls)

    POST_INIT = '__post_init__'

    def init(self, instance, args, kwargs, force_reinit=False):
        if not force_reinit and self.is_initialized(instance):
            return

        context = Namespace(missing=set())
        bound = self.signature.bind(*args, **kwargs)
        arguments = bound.arguments

        all_arguments = {
            **{argument_name: MISSING for argument_name in self.signature.parameters},
            **arguments
        }

        for argument, value in all_arguments.items():
            parameter = self.data[argument]
            parameter.set(argument, context, instance=instance, value=value)

        missing = context.missing
        if missing:
            cls_name = type(instance).__name__
            raise TypeError(
                f'{cls_name}.__init__() missing {len(missing)} '
                f'required argument(s): {", ".join(missing)}'
            )

        self.mark_initialized(instance)

    def post_init(self, instance):
        post_init = getattr(instance, self.POST_INIT, None)
        if callable(post_init):
            post_init()

    @property
    def parameters(self):
        return self.data

    @property
    def attributes(self):
        return tuple(
            name
            for name, param in self.parameters.items()
            if param.attribute is not None
        )

    def __repr__(self):
        return ', '.join(map(repr, self.parameters.values())).join('()')


def _generic_reflection(tp):
    reflection = None
    if hasattr(tp, '_nparams'):
        orig = typing.get_origin(tp)
        reflection = orig, tp
    return reflection


_GENERIC_REFLECTIONS = dict(filter(None, map(_generic_reflection, vars(typing).values())))


def _get_nparams(origin):
    origin = _GENERIC_REFLECTIONS.get(origin, origin)
    return getattr(origin, '_nparams', None)


def _hint_coercion_factory(hint):
    # Correctly handle Generic types
    # Not that correctly the Annotated ones
    origin = typing.get_origin(hint)
    args = collections.deque(typing.get_args(hint))

    if origin and args:
        if _get_nparams(origin) == -1:
            expected = len(args)

            def coerce_func(obj):
                passed = len(obj)
                if passed != expected:
                    raise CoercionError(f'expected {expected} argument(s), got {passed}')
                return obj

        else:
            coerce_func = None
        data_type = origin
        if origin in (typing.Annotated, typing.Generic):
            data_type = None
        elif issubclass(origin, types.UnionType):
            return SelectCoercion(*map(hint_coercion, args))
        elif origin in (type, typing.Type):
            def coerce_func(cls):
                if not issubclass(cls, tuple(args)):
                    raise CoercionError(f'expected {hint}')
                return cls
            return Coercion(
                data_type=type,
                post_conversion=coerce_func
            )
        result_coercion = Coercion(
            data_type=data_type,
            pre_conversion=coerce_func
        )
        coercion = RecursiveCoercion(result_coercion=result_coercion)
        while args:
            tp = args.popleft()
            if tp is ...:
                # No length coercion, ellipsis allows indefinite amount of elements
                result_coercion.pre_conversion = None
            else:
                coercion.element_coercion = hint_coercion(tp)
        return coercion

    # ...and non-generic ones
    return Coercion(hint)


_dispatch = functools.singledispatch(_hint_coercion_factory)
_hint_register = _dispatch.register


def hint_coercion(tp):
    try:
        weakref.ref(tp)
    except TypeError:
        return _hint_coercion_factory(tp)
    return _dispatch.dispatch(tp)(tp)


def coercion_factory(fn, tp=None):
    if tp is None:
        return functools.partial(coercion_factory, fn)
    _hint_register(tp)(fn)
    return tp


def attribute_predicate(member, hints):
    name, value = member
    return name in hints or isinstance(value, Parameter)


def generate_dataclass_constructor(
    cls,
    attributes=None,
):
    hints = typing.get_type_hints(cls)
    if attributes is None:
        ordered_hints = tuple(hints)
        attributes = sorted(
            dict(
                filter(
                    functools.partial(attribute_predicate, hints=hints),
                    dict(inspect.getmembers(cls), **hints).items()
                )
            ),
            key=lambda obj: ordered_hints.index(obj) if obj in ordered_hints else INFINITE
        )
    args = {}
    kw_only = False
    for attribute in attributes:
        coercion = None
        hint = hints.get(attribute)
        if hint:
            coercion = hint_coercion(hint)
        if hint is Parameter.KW_ONLY:
            if kw_only:
                raise ConstructorError('duplicated * in constructor signature')
            kw_only = True
            continue
        value = getattr(cls, attribute, MISSING)
        if isinstance(value, Parameter):
            param = value
            args[attribute] = param
            if coercion:
                param.add_coercion(coercion, location='fb', _is_hint_coercion=hint is not None)
            if kw_only:
                if value.kind < Parameter.POSITIONAL_OR_KEYWORD:
                    raise ConstructorError(
                        'illegal parameter kind to be followed by * in constructor '
                        'signature'
                    )
        else:
            param = Parameter(coercion, default=value)
            args[attribute] = param
        if param.is_factory_key:
            factory_key = cls.__constructor_factory_key__ or ()
            if isinstance(factory_key, str):
                factory_key = factory_key.replace(',', ' ').split()
            if attribute not in factory_key:
                factory_key = (*factory_key, attribute)
            cls.__constructor_factory_key__ = factory_key
        if kw_only:
            param.kind = Parameter.KEYWORD_ONLY
        if param.kind == Parameter.VAR_POSITIONAL:
            kw_only = True
    kwargs = cls.__constructor_kwargs__
    constructor = Constructor(args, **kwargs)
    if cls.__constructor__:
        cls.__constructor__ = Constructor({**cls.__constructor__, **constructor})
    else:
        cls.__constructor__ = constructor
    return constructor
