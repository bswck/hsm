from hsm.core import BasicExpression
from hsm.const import *
from hsm.core import x, y, z


subtraction = BasicExpression('sub', 2, 0, 3, 6)
print(subtraction)
addition = subtraction.reassemble('add')
print(addition)
print(addition.reassemble('commutate'))
