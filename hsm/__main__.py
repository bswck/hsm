from hsm.ops.operand import AtomicOperationNode


subtraction = AtomicOperationNode('sub', 2, 0, 3, 6)
print(subtraction)
addition = subtraction.convert()
print(addition)
print(addition.reassemble('commutate'))
