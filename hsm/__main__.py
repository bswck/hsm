from hsm.core import Operation
from hsm.const import *
from hsm.core import x, y, z


subtraction = Operation('sub', 2, 0, 3, 6)
print(subtraction)
addition = subtraction.reassemble('add')
print(addition)
print(addition.reassemble('commutate'))
