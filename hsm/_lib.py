import collections
import functools
import inspect
import itertools
import keyword
import re
import sys
import types
import typing
import weakref


class HSMError(Exception):
    """HSM error."""


class CoercionFailureError(HSMError):
    MSG_DEFAULT = 'no additional information'

    def __init__(self, obj=None):
        if isinstance(obj, str):
            self.msg = obj
        elif isinstance(obj, bool):
            self.msg = self.MSG_DEFAULT
        self.args = self.msg,

    def __bool__(self):
        return False

    def __new__(cls, coercion_failure=None):
        if isinstance(coercion_failure, cls):
            return coercion_failure
        return object.__new__(cls)


class _HSMMeta(type):
    if __debug__:
        __constructor__: 'Constructor'
        ops = None

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
        if cls.ops is None:
            cls.ops = OperatorDispatcher()

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
            return f'(special sentinel value)'


MISSING = _Sentinel()
INFINITE = float('inf')


class CoercionBase:
    pass


class Coercion(CoercionBase):
    """Simple single-value coercion."""
    # Technical detail: don't make `data_type' and `validator' class variables.

    def __init__(
        self,
        data_type=None,
        validator=None,
        cast=MISSING,
        objective_validator=None,
    ):
        if not isinstance(data_type, type):
            validator = validator
            data_type = None
        if not hasattr(self, 'data_type'):
            self.data_type = data_type
        if not hasattr(self, 'validator'):
            self.validator = validator
        if cast is MISSING:
            cast = self.data_type
        self.cast = cast
        self.objective_validator = objective_validator

    def __new__(cls, *args, **kwargs):
        if args and isinstance(args[0], CoercionBase):
            return args[0]
        return object.__new__(cls)

    @staticmethod
    def call_validator(validator, value):
        """Call object validator and ensure to include additional failure context, if provided."""

        if callable(validator):
            valid = validator(value)
            if isinstance(value, str) or not valid:
                failure = CoercionFailureError(valid)
                raise failure from None

    def coerce_valid(self, value):
        """Try to coerce a valid value in a mathematical object construction."""

        data_type = self.data_type
        objective_validator = self.objective_validator
        validator = self.validator

        # Expected data type is provided, examine the value with reference to it.
        if data_type is not None:
            if isinstance(value, data_type):
                # Value is of the proper data type.
                obj = value
            else:
                # Need to cast the value to the proper data type.
                # Validate before trying, then cast, and let the errors propagate if any.
                self.call_validator(validator, value)
                if callable(self.cast):
                    obj = self.cast(value)
                else:
                    obj = value
        # Expected data type is not provided, we assume the value is of an acceptable data type.
        else:
            obj = value

        # Validate the object of an acceptable data type.
        self.call_validator(objective_validator, obj)
        return obj

    if __debug__:
        def __repr__(self):
            repr_string = f'<%s{type(self).__name__}%s>'
            repr_chunks = []
            if self.data_type:
                repr_chunks.append(f'type={self.data_type.__name__}')
            if self.validator and self.validator is not self.data_type:
                repr_chunks.append(f'validator={self.validator}')
            if self.cast is not self.data_type:
                repr_chunks.append(f'cast={self.cast}')
            if not repr_chunks:
                return repr_string % ('Null', '')
            return repr_string % ('', ' ' + ' '.join(repr_chunks))


class RecursiveCoercion(CoercionBase):
    class _LazyCollectionCoercion:
        def __init__(self, coercion, iterable, depth):
            self.coercion = coercion
            self.iterator = iter(iterable)
            self.depth = depth

        def __next__(self):
            next_obj = next(self.iterator)
            return self.coercion.coerce_valid(next_obj, depth=self.depth)

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

    def coerce_valid(self, value, depth=0):
        if isinstance(value, self.iterable_types):
            if 0 < depth <= self.recursion_depth:
                if self.lazy:
                    return self._LazyCollectionCoercion(self, value, depth+1)
                valid_elems = []
                for elem in value:
                    valid_elems.append(self.coerce_valid(elem, depth+1))
                return valid_elems
        if depth > self.recursion_depth:
            return self.element_coercion.coerce_valid(value)
        return self.result_coercion.coerce_valid(value)

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


class UnionCoercion(CoercionBase):
    def __init__(self, *allowed_types):
        self.data_type = allowed_types

    def coerce_valid(self, value):
        return Coercion.coerce_valid(typing.cast(Coercion, self), value)


identity = Coercion()


class Parameter:
    KW_ONLY = _Sentinel()

    def __init__(
        self,
        default=MISSING,
        default_factory=None,
        instance_factory=False,
        coercion=None,
        attribute=MISSING,
        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        self.default = default
        self.default_factory = default_factory
        self.instance_factory = instance_factory
        self.attribute = attribute
        self.coercion = coercion or identity
        self.kind = kind

        self.__default_name = None

    ERROR = _Sentinel()

    def set(self, instance, name, context, value=MISSING):
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
                    context.missing.add(name)
                    return self.ERROR
            else:
                value = default
        obj = self.coercion.coerce_valid(value)
        attribute = self.attribute
        if attribute is MISSING:
            attribute = name
        if isinstance(attribute, str):
            setattr(instance, attribute, obj)
        return obj

    def to_inspect_obj(self, name):
        self.__default_name = name
        return inspect.Parameter(
            name=name,
            kind=self.kind,
            default=self.default
        )

    VAR_POS_PREFIX = '*'
    VAR_KW_PREFIX = '**'
    DEFAULT_JOIN = '='
    DEFAULTF_JOIN = '->'
    DEFAULTFI_JOIN = '~>'
    UNNAMED = '(unnamed)'

    PAT = re.compile(
        rf'(?P<variadic_prefix>{re.escape(VAR_POS_PREFIX)}|{re.escape(VAR_KW_PREFIX)})'
        rf'(?P<name>\S+)((?P<join>{DEFAULT_JOIN}|{DEFAULTF_JOIN}|{DEFAULTFI_JOIN})'
        rf'(?P<default>.*))?'
    )

    @classmethod
    def from_str(cls, string, coercion=None, default_parse=eval):
        inst = cls(coercion=Coercion(coercion))
        match = cls.PAT.match(string)
        if match:
            data = match.groupdict()
            variadic_prefix = data['variadic_prefix']
            name = data['name']
            default = data.get('default', MISSING)
            default_is_factory = data.get('join') in (cls.DEFAULT_JOIN, cls.DEFAULTFI_JOIN)
            if default_is_factory:
                inst.instance_factory = data.get('join') == cls.DEFAULTFI_JOIN
            if variadic_prefix == cls.VAR_POS_PREFIX:
                inst.kind = inspect.Parameter.VAR_POSITIONAL
            if variadic_prefix == cls.VAR_POS_PREFIX:
                inst.kind = inspect.Parameter.VAR_KEYWORD
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
            if self.kind > inspect.Parameter.POSITIONAL_OR_KEYWORD:
                if self.kind == inspect.Parameter.POSITIONAL_ONLY:
                    repr_string = self.VAR_POS_PREFIX + repr_string
                elif self.kind == inspect.Parameter.KEYWORD_ONLY:
                    repr_string = self.VAR_KW_PREFIX + repr_string
            default_obj = self.default or self.default_factory
            const = default_obj is self.default
            if default_obj:
                join = (
                    (self.DEFAULTF_JOIN, self.DEFAULTFI_JOIN)[self.instance_factory],
                    self.DEFAULT_JOIN
                )[const]
                repr_string += join + repr(default_obj).join('()')
            return repr_string


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
                d = self.signature.bind(*args, **kwargs).arguments
                key = tuple(d[arg_name] for arg_name in arg_names)

            if key is MISSING:
                raise ValueError('invalid key maker for factory constructor')

            # Important, don't reference the instance
            try:
                return self.instances[key]
            except KeyError:
                ref = object.__new__(cls)
                self.instances[key] = ref
                return self.instances[key]

        return object.__new__(cls)

    POST_INIT = '__post_init__'

    def init(self, instance, args, kwargs):
        context = Namespace(missing=set())
        arguments = self.signature.bind(*args, **kwargs).arguments
        for argument, value in {
            **{arg_name: MISSING for arg_name in self.signature.parameters},
            **arguments
        }.items():
            parameter = self.data[argument]
            parameter.set(instance, argument, context, value)
        missing_args = context.missing
        if missing_args:
            cls_name = type(instance).__name__
            raise TypeError(
                f'{cls_name}.__init__() missing {len(missing_args)} '
                f'required argument(s): {", ".join(missing_args)}'
            )
        post_init = getattr(instance, self.POST_INIT, None)
        if callable(post_init):
            post_init(instance)

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
            validator = (lambda obj: len(obj) == len(args))
        else:
            validator = None
        data_type = origin
        if origin in (typing.Annotated, typing.Generic):
            data_type = None
        elif issubclass(origin, types.UnionType):
            return UnionCoercion(
                *map(coercion_from_hint, args)
            )
        result_coercion = Coercion(
            data_type=data_type,
            validator=validator
        )
        coercion = RecursiveCoercion(result_coercion)
        while args:
            arg = args.popleft()
            if arg is ...:
                # No length validator, ellipsis allows indefinite amount of elements
                result_coercion.validator = None
            else:
                coercion.element_coercion = coercion_from_hint(arg)
        return coercion

    # ...and non-generic ones
    return Coercion(hint)


def generate_class_constructor(cls, only_attrs=None):
    hints = typing.get_type_hints(cls)
    if only_attrs is None and cls.__constructor_scan_annotations__:
        only_attrs = tuple(attr for attr in hints)
    args = {}
    make_kw_only = False
    for attr in only_attrs:
        coercion = None
        hint = hints.get(attr)
        if hint:
            coercion = coercion_from_hint(hint)
        value = getattr(cls, attr, MISSING)
        if isinstance(value, Parameter):
            param = value
            if coercion:
                param.coercion = coercion
            args[attr] = param
            if make_kw_only:
                if value.kind < inspect.Parameter.POSITIONAL_OR_KEYWORD:
                    raise HSMError(
                        'illegal parameter kind to be followed by * in constructor '
                        'signature'
                    )
        else:
            param = Parameter(default=value, coercion=coercion)
            args[attr] = param
        if make_kw_only:
            param.kind = inspect.Parameter.KEYWORD_ONLY
        if value is Parameter.KW_ONLY:
            if make_kw_only:
                raise HSMError('duplicated * in constructor signature')
            make_kw_only = True
            del args[attr]
    kwargs = cls.__constructor_kwargs__
    constructor = Constructor(args, **kwargs)
    cls.__constructor__ = constructor
    return constructor


class OperatorDispatcher:
    def abs(self, fn, *args, **kwargs):
        pass

    def add(self, fn, *args, **kwargs):
        pass

    def and_(self, fn, *args, **kwargs):
        pass

    def concat(self, fn, *args, **kwargs):
        pass

    def contains(self, fn, *args, **kwargs):
        pass

    def count_of(self, fn, *args, **kwargs):
        pass

    def delitem(self, fn, *args, **kwargs):
        pass

    def eq(self, fn, *args, **kwargs):
        pass

    def floordiv(self, fn, *args, **kwargs):
        pass

    def ge(self, fn, *args, **kwargs):
        pass

    def getitem(self, fn, *args, **kwargs):
        pass

    def gt(self, fn, *args, **kwargs):
        pass

    def iadd(self, fn, *args, **kwargs):
        pass

    def iand(self, fn, *args, **kwargs):
        pass

    def iconcat(self, fn, *args, **kwargs):
        pass

    def ifloordiv(self, fn, *args, **kwargs):
        pass

    def ilshift(self, fn, *args, **kwargs):
        pass

    def imatmul(self, fn, *args, **kwargs):
        pass

    def imod(self, fn, *args, **kwargs):
        pass

    def imul(self, fn, *args, **kwargs):
        pass

    def index(self, fn, *args, **kwargs):
        pass

    def index_of(self, fn, *args, **kwargs):
        pass

    def invert(self, fn, *args, **kwargs):
        pass

    inv = invert

    def ior(self, fn, *args, **kwargs):
        pass

    def ipow(self, fn, *args, **kwargs):
        pass

    def irshift(self, fn, *args, **kwargs):
        pass

    def is_(self, fn, *args, **kwargs):
        pass

    def is_not(self, fn, *args, **kwargs):
        pass

    def isub(self, fn, *args, **kwargs):
        pass

    def itemgetter(self, fn, *args, **kwargs):
        pass

    def itruediv(self, fn, *args, **kwargs):
        pass

    def ixor(self, fn, *args, **kwargs):
        pass

    def le(self, fn, *args, **kwargs):
        pass

    def length_hint(self, fn, *args, **kwargs):
        pass

    def lshift(self, fn, *args, **kwargs):
        pass

    def lt(self, fn, *args, **kwargs):
        pass

    def matmul(self, fn, *args, **kwargs):
        pass

    def methodcaller(self, fn, *args, **kwargs):
        pass

    def mod(self, fn, *args, **kwargs):
        pass

    def mul(self, fn, *args, **kwargs):
        pass

    def ne(self, fn, *args, **kwargs):
        pass

    def neg(self, fn, *args, **kwargs):
        pass

    def not_(self, fn, *args, **kwargs):
        pass

    def or_(self, fn, *args, **kwargs):
        pass

    def pos(self, fn, *args, **kwargs):
        pass

    def pow(self, fn, *args, **kwargs):
        pass

    def rshift(self, fn, *args, **kwargs):
        pass

    def setitem(self, fn, *args, **kwargs):
        pass

    def sub(self, fn, *args, **kwargs):
        pass

    def truediv(self, fn, *args, **kwargs):
        pass

    def truth(self, fn, *args, **kwargs):
        pass

    def xor(self, fn, *args, **kwargs):
        pass

    _ops_to_fns = {
        sys.intern('abs'): abs,
        sys.intern('+'): add,
        sys.intern('&'): and_,
        sys.intern('+'): concat,
        sys.intern('in'): contains,
        sys.intern('del'): delitem,
        sys.intern('=='): eq,
        sys.intern('//'): floordiv,
        sys.intern('>='): ge,
        sys.intern('[]'): getitem,
        sys.intern('>'): gt,
        sys.intern('+='): iadd,
        sys.intern('&='): iand,
        sys.intern('+=,'): iconcat,
        sys.intern('//='): ifloordiv,
        sys.intern('<<='): ilshift,
        sys.intern('@='): imatmul,
        sys.intern('%='): imod,
        sys.intern('*='): imul,
        sys.intern('index'): index,
        sys.intern('~'): invert,
        sys.intern('|='): ior,
        sys.intern('**='): ipow,
        sys.intern('>>='): irshift,
        sys.intern('is'): is_,
        sys.intern('is not'): is_not,
        sys.intern('-='): isub,
        sys.intern('/='): itruediv,
        sys.intern('^='): ixor,
        sys.intern('<='): le,
        sys.intern('<<'): lshift,
        sys.intern('<'): lt,
        sys.intern('@'): matmul,
        sys.intern('%'): mod,
        sys.intern('*'): mul,
        sys.intern('!='): ne,
        sys.intern('neg'): neg,
        sys.intern('not'): not_,
        sys.intern('|'): or_,
        sys.intern('**'): pow,
        sys.intern('>>'): rshift,
        sys.intern('[]='): setitem,
        sys.intern('-'): sub,
        sys.intern('/'): truediv,
        sys.intern('^'): xor,
    }

    def op(self, ch):
        return functools.partial(self._ops_to_fns[sys.intern(ch)], self)
