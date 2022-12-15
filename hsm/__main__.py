from hsm.arith.op import AtomicOperation


subtraction = AtomicOperation('sub', 2, 0, 3, 6)
print(subtraction)
addition = subtraction.convert()
print(addition)
print(addition.reassemble('commutate'))
