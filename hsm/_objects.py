import collections
import functools
import inspect
import itertools
import keyword
import re
import types
import typing
import weakref


class HSMError(Exception):
    """HSM error."""


class CoercionFailureError(HSMError):
    MSG_DEFAULT = 'no additional information'

    def __init__(self, obj=None, param_name=None):
        if isinstance(obj, str):
            self.msg = obj
        elif isinstance(obj, bool):
            self.msg = self.MSG_DEFAULT
        self._param_name = None
        self.args = self.msg,
        self.param_name = param_name

    @property
    def param_name(self):
        return self._param_name

    @param_name.setter
    def param_name(self, name):
        self._param_name = name
        self.args = ' '.join((self.msg.strip(), f'(parameter {name!r})')),

    def __bool__(self):
        return False

    def __new__(cls, coercion_failure=None, param_name=None):
        if isinstance(coercion_failure, cls):
            return coercion_failure
        return HSMError.__new__(cls)


class _HSMMeta(type):
    if __debug__:
        __constructor__: 'Constructor'
        __ops__ = None

        def __repr__(self):
            constructor = self.__constructor__
            if constructor:
                return (
                    f'<class {self.__qualname__}'
                    f'{", ".join(map(repr, constructor.parameters.values())).join("()")}>'
                )
            return type.__repr__(self)


class Object(metaclass=_HSMMeta):
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

    def __init_subclass__(cls, generate_constructor=True, factory_key=None):
        if factory_key:
            cls.__constructor_factory_key__ = factory_key
        if generate_constructor and cls.__constructor__ is None:
            constructor = generate_class_constructor(cls)
            factory_key_maker = cls.__constructor_factory_key__
            if constructor and factory_key_maker:
                constructor.factory_key_maker = factory_key_maker

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
    # Technical detail: don't make `data_type' and `coercer' class variables.

    def __init__(
        self,
        data_type=None,
        before_cast=None,
        cast=MISSING,
        after_cast=None,
    ):
        if not isinstance(data_type, type):
            before_cast = data_type
            data_type = None
        if not hasattr(self, 'data_type'):
            if isinstance(data_type, str):
                before_cast = coercion_from_hint(data_type).coerce
                data_type = None
            self.data_type = data_type
        if not hasattr(self, 'coercer'):
            self.before_cast = before_cast
        if cast is MISSING:
            cast = self.data_type
        self.cast = cast
        self.after_cast = after_cast

    def __new__(cls, *args, **kwargs):
        if args and isinstance(args[0], CoercionBase):
            return args[0]
        return object.__new__(cls)

    @staticmethod
    def _coerce(coercer, value, name=None):
        """Call object coercer and ensure to include additional failure context, if provided."""

        if callable(coercer):
            try:
                valid = coercer(value)
            except CoercionFailureError as failure:
                failure.param_name = name
                raise failure from None
            return valid
        return value

    def coerce(self, value, name=None):
        """Try to coerce a valid value in a mathematical object construction."""

        data_type = self.data_type
        before_cast = self.before_cast
        after_cast = self.after_cast

        # Expected data type is provided, examine the value with reference to it.
        if data_type is not None:
            if isinstance(value, data_type):
                # Value is of the proper data type.
                obj = value
            else:
                # Need to cast the value to the proper data type.
                # Validate before trying, then cast, and let the errors propagate if any.
                value = self._coerce(before_cast, value, name=name)
                if callable(self.cast):
                    try:
                        obj = self.cast(value)
                    except Exception as exc:
                        raise CoercionFailureError(
                            f'could not cast {type(value).__name__} {value!r} '
                            f'to {data_type.__name__}',
                            param_name=name
                        ) from exc
                else:
                    obj = value
        # Expected data type is not provided, we assume the value is of an acceptable data type.
        else:
            obj = value

        # Validate the object of an acceptable data type.
        obj = self._coerce(after_cast, obj, name=name)
        return obj

    if __debug__:
        def __repr__(self):
            repr_string = f'<%s{type(self).__name__}%s>'
            repr_chunks = []
            if self.data_type:
                repr_chunks.append(f'type={self.data_type.__name__}')
            if self.before_cast and self.before_cast is not self.data_type:
                repr_chunks.append(f'before_cast={self.before_cast}')
            if self.cast is not self.data_type:
                repr_chunks.append(f'cast={self.cast}')
            if self.after_cast:
                repr_chunks.append(f'after_cast={self.after_cast}')
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
        self.result_coercion = Coercion(result_coercion)
        self.element_coercion = Coercion(element_coercion)
        self.iterable_types = iterable_types
        self.recursion_depth = recursion_depth
        self.lazy = lazy

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
    def __init__(self, *coercions):
        self.coercions = coercions

    def coerce(self, value, name=None):
        valid = MISSING
        for coercion in self.coercions:
            try:
                valid = coercion.coerce(value, name=name)
            except (HSMError, ValueError):
                pass
            if valid is not MISSING:
                return value

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
        instance_factory=False,
        attribute=MISSING,
        kind=POSITIONAL_OR_KEYWORD,
    ):
        self.default = default
        self.default_factory = default_factory
        self.instance_factory = instance_factory
        self.attribute = attribute
        self.coercions = list(coercions)
        self.kind = kind

        self.__default_name = None

    ERROR = _Sentinel()

    def add_coercion(self, coercion, pos='f'):
        if 'f' in pos:
            self.coercions.insert(0, coercion)
        if 'b' in pos:
            self.coercions.append(coercion)

    def remove_coercion(self, coercion):
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
                        context.missing.add(name)
                        return self.ERROR
            else:
                value = default
        obj = functools.reduce(lambda v, c: c.coerce(v, name=name), self.coercions, value)
        if instance is not None:
            attribute = self.attribute
            if attribute is MISSING:
                attribute = name
            if isinstance(attribute, str):
                setattr(instance, attribute, obj)
        return obj

    def to_inspect_obj(self, name):
        self.__default_name = name
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
    UNNAMED = '(unnamed)'

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

    if __debug__:
        def __repr__(self):
            return self.repr(name=self.__default_name or 'argument')

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
                repr_string += join + repr(default_obj).join('()')
            return repr_string


Args = functools.partial(Parameter, kind=Parameter.VAR_POSITIONAL)
KWArgs = functools.partial(Parameter, kind=Parameter.VAR_KEYWORD)


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
    def __init__(self, other=None, /, **kwargs):
        super().__init__(other)
        if not hasattr(self, 'instances'):
            self.instances = weakref.WeakValueDictionary()
        if kwargs:
            self.update(kwargs)
        self.initialized = weakref.WeakSet()
        self.signature = None
        if not hasattr(self, 'factory_key_maker'):
            self.factory_key_maker = None
        self.validate_parameters()

    def validate_parameters(self):
        parameters = list(itertools.starmap(
            lambda name, param: param.to_inspect_obj(name),
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
        constructor.factory_key_maker = key_maker
        return constructor

    def new(self, cls, args, kwargs):
        key_maker = self.factory_key_maker
        key = MISSING

        if key_maker:
            if callable(key_maker):
                key = key_maker()
            elif isinstance(key_maker, (str, tuple)):
                if isinstance(key_maker, str):
                    arg_names = key_maker.replace(' ', ',').split(',')
                else:
                    arg_names = key_maker
                # Unfortunately we cannot use ._bind() since it is private,
                # thus it's needed to iter over args and kwargs again and again. :(
                bound = self.signature.bind(*args, **kwargs).arguments
                missing = set()
                key = []
                for arg_name in arg_names:
                    param = self.parameters[arg_name]
                    try:
                        specified_value = bound[arg_name]
                    except KeyError:
                        if (
                            param.default is MISSING
                            and param.default_factory
                            and param.instance_factory
                        ):
                            raise ValueError(
                                'constructor factory key parameter cannot take instance'
                                'as an argument, because it can be not created yet'
                            ) from None
                        value = param.set(arg_name, Namespace(missing=missing))
                        if value is not MISSING:
                            key.append(value)
                    else:
                        value = param.set(
                            arg_name,
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
                raise ValueError('invalid key maker for factory constructor')

            try:
                return self.instances[key]
            except KeyError:
                inst_ref = object.__new__(cls)
                self.instances[key] = inst_ref
                return inst_ref

        return object.__new__(cls)

    POST_INIT = '__post_init__'

    def init(self, instance, args, kwargs, force=False):
        if not force and instance in self.initialized:
            return
        context = Namespace(missing=set())
        arguments = self.signature.bind(*args, **kwargs).arguments
        for argument, value in {
            **{arg_name: MISSING for arg_name in self.signature.parameters},
            **arguments
        }.items():
            parameter = self.data[argument]
            parameter.set(argument, context, instance=instance, value=value)
        missing_args = context.missing
        if missing_args:
            cls_name = type(instance).__name__
            raise TypeError(
                f'{cls_name}.__init__() missing {len(missing_args)} '
                f'required argument(s): {", ".join(missing_args)}'
            )
        post_init = getattr(instance, self.POST_INIT, None)
        if callable(post_init):
            post_init()
        self.initialized.add(instance)

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


def coercion_from_hint(hint):
    # Correctly handle Generic types
    origin = typing.get_origin(hint)
    args = collections.deque(typing.get_args(hint))

    if origin and args:
        if getattr(origin, '_nparams', None) == -1:
            coercer = (lambda obj: len(obj) == len(args))
        else:
            coercer = None
        data_type = origin
        if origin in (typing.Annotated, typing.Generic):
            data_type = None
        elif issubclass(origin, types.UnionType):
            return SelectCoercion(
                *map(coercion_from_hint, args)
            )
        elif origin in (type, typing.Type):
            def type_coercer(typ):
                if not issubclass(typ, tuple(args)):
                    raise CoercionFailureError(f'expected {hint}')
            return Coercion(
                data_type=type,
                after_cast=type_coercer
            )
        result_coercion = Coercion(
            data_type=data_type,
            before_cast=coercer
        )
        coercion = RecursiveCoercion(result_coercion)
        while args:
            arg = args.popleft()
            if arg is ...:
                # No length coercer, ellipsis allows indefinite amount of elements
                result_coercion.before_cast = None
            else:
                coercion.element_coercion = coercion_from_hint(arg)
        return coercion

    # ...and non-generic ones
    return Coercion(hint)


def generate_class_constructor(cls, only_attrs=None):
    hints = typing.get_type_hints(cls)
    if only_attrs is None and cls.__constructor_scan_annotations__:
        only_attrs = tuple(attr for attr in hints)
    else:
        only_attrs = tuple()
    args = {}
    make_kw_only = False
    for attr in only_attrs:
        coercion = None
        hint = hints.get(attr)
        if hint is Parameter.KW_ONLY:
            if make_kw_only:
                raise HSMError('duplicated * in constructor signature')
            make_kw_only = True
            continue
        if hint:
            coercion = coercion_from_hint(hint)
        value = getattr(cls, attr, MISSING)
        if isinstance(value, Parameter):
            param = value
            if coercion:
                param.coercions.insert(0, coercion)
            args[attr] = param
            if make_kw_only:
                if value.kind < Parameter.POSITIONAL_OR_KEYWORD:
                    raise HSMError(
                        'illegal parameter kind to be followed by * in constructor '
                        'signature'
                    )
        else:
            param = Parameter(coercion, default=value)
            args[attr] = param
        if make_kw_only:
            param.kind = Parameter.KEYWORD_ONLY
    kwargs = cls.__constructor_kwargs__
    constructor = Constructor(args, **kwargs)
    cls.__constructor__ = constructor
    return constructor
