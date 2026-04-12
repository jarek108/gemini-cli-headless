
from container import DIContainer, CircularDependencyError
import sys

class A:
    def __init__(self, b: 'B'):
        self.b = b

class B:
    def __init__(self, a: A):
        self.a = a

def test():
    container = DIContainer()
    # Add the current module's globals so 'B' can be resolved
    container.add_scope(globals())
    
    try:
        container.resolve(A)
    except CircularDependencyError:
        print("SUCCESS: CircularDependencyError raised")
    except Exception as e:
        print(f"FAILURE: Raised {type(e).__name__}: {e}")
    else:
        print("FAILURE: No exception raised")

if __name__ == "__main__":
    test()
