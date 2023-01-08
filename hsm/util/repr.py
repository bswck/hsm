"""Object representation recipes of an advanced configurability."""
# could be rewritten to support string seek and tell
import functools
import operator


HSM_REPR = (tuple,)
FLAG = '__repr_hsm__'


# if you want to register your representation to hsm...
# use repr_object.register()
@functools.singledispatch
def repr_object(
        obj,
        attributes=None,
        repr_names=None,
        prefix=None,
        brackets='()',
        surrounding_brackets=None,
        ignore_flag=False,
        **kwds,
):
    """Represent an object defined in the library."""
    if not ignore_flag and not getattr(obj, FLAG, False):
        return repr(obj)
    if prefix is None:
        kwds.update(surrounding_brackets=surrounding_brackets)
        if isinstance(obj, type):
            named_obj = obj
            surrounding_brackets = surrounding_brackets or ('<class ', '>')
        else:
            named_obj = type(obj)
        prefix = named_obj.__qualname__
    surrounding_brackets = surrounding_brackets or ('', '')
    kwds.update(prefix=prefix, brackets=brackets)
    if hasattr(obj, '__dict__'):
        name_list = attributes or [
            name for name in vars(obj)
            if not name.startswith('_')
        ]
        if repr_names is None:
            repr_names = len(name_list) > 1
        if len(name_list) == 1:
            if kwds.get('split'):
                kwds.update(brackets=None)
            kwds.update(surrounding_brackets=None, split=False)
        return repr_map(
            map_obj=name_list,
            repr_names=repr_names,
            accessor=lambda _, name: getattr(obj, name),
            **kwds
        ).join(surrounding_brackets)
    return (prefix + repr(obj).join(brackets)).join(surrounding_brackets)


def repr_map(
        map_obj,
        repr_names=True,
        ident=0,
        split=None,
        prefix='',
        mapper=None,
        brackets='()',
        surrounding_brackets=None,
        sep=',',
        accessor=operator.getitem
):
    mapper = mapper or (lambda name, item, i=0: repr_object(item))

    def wrapper(item, i=0):
        mapped = mapper(item, accessor(map_obj, item), i)
        return f'{item}={mapped}' if repr_names else mapped

    return repr_collection(
        collection=map_obj, ident=ident, split=split,
        prefix=prefix, mapper=wrapper, brackets=brackets,
        surrounding_brackets=surrounding_brackets, sep=sep
    )


def repr_collection(
        collection,
        ident=0,
        split=None,
        prefix='',
        mapper=None,
        brackets='()',
        surrounding_brackets=None,
        sep=',',
        ignore_flag=False
):
    if callable(split):
        split = split(repr_collection(
            collection, ident, split=True, prefix=prefix, mapper=mapper, brackets=brackets,
            surrounding_brackets=surrounding_brackets, sep=sep, ignore_flag=ignore_flag
        ))
    if split is None:
        split = bool(ident)
    mapper = mapper or (lambda item, i=0: repr_object(item, ignore_flag=ignore_flag))
    lb, rb = (brackets or ('', ''))
    ident_string = ('\n' + ' ' * ident) if split else ''
    repr_string = prefix + lb + ident_string
    repr_string += (sep + ('\n' if split else ' ')).join(
        f'{mapper(item, ident)}'
        for item in collection
    ).replace('\n', ident_string or '\n')
    repr_string += ('\n' if split else '') + rb
    return repr_string.join(surrounding_brackets) if surrounding_brackets else repr_string


nested_repr_collection = functools.partial(repr_collection, split=True)
