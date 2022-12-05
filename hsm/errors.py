class HSMError(Exception):
    pass


class ConstructorError(HSMError):
    pass


class CoercionError(HSMError):
    MSG_DEFAULT = 'no information'

    def __init__(self, obj=None, param=None):
        if isinstance(obj, str):
            self.msg = obj
        elif isinstance(obj, bool):
            self.msg = self.MSG_DEFAULT
        self._param = None
        self.args = self.msg,
        self.param = param

    @property
    def param(self):
        return self._param

    @param.setter
    def param(self, param):
        self._param = param
        self.args = ' '.join((
            self.msg.strip(),
            *((f'(parameter {param!r})',) if param else ())
        )),

    def __bool__(self):
        return False

    def __new__(cls, obj=None, name=None):
        if isinstance(obj, cls):
            return obj
        return Exception.__new__(cls)
