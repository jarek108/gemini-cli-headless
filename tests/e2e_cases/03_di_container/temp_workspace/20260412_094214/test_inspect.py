
import inspect
class A: pass
print(f"A: {inspect.signature(A)}")
class B:
    def __init__(self, x: int):
        pass
print(f"B: {inspect.signature(B)}")
