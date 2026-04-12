import unittest
from container import DIContainer, CircularDependencyError
import inspect

class A:
    def __init__(self):
        pass

class B:
    def __init__(self, a: A):
        self.a = a

class C:
    def __init__(self, b: B):
        self.b = b

# To test circular dependency without string annotations
class Circular1:
    def __init__(self, c2: 'Circular2'): # Still using string for the class def
        self.c2 = c2

class Circular2:
    def __init__(self, c1: Circular1):
        self.c1 = c1

# Manual patching to avoid string annotation issues in resolve
class SyncA:
    pass

class SyncB:
    def __init__(self, a: SyncA):
        self.a = a

def sync_a_init(self, b: SyncB):
    self.b = b

SyncA.__init__ = sync_a_init
# Manually set annotations so inspect can see them as classes, not strings
SyncA.__init__.__annotations__ = {'b': SyncB}

class DefaultValue:
    def __init__(self, value: int = 10):
        self.value = value

class NoTypeHint:
    def __init__(self, something):
        self.something = something

class TestDIContainer(unittest.TestCase):
    def setUp(self):
        self.container = DIContainer()

    def test_singleton(self):
        a_instance = A()
        self.container.register_singleton(A, a_instance)
        self.assertEqual(self.container.resolve(A), a_instance)
        self.assertEqual(self.container.resolve(A), a_instance)

    def test_factory(self):
        self.container.register_factory(A, lambda: A())
        a1 = self.container.resolve(A)
        a2 = self.container.resolve(A)
        self.assertIsNot(a1, a2)
        self.assertIsInstance(a1, A)
        self.assertIsInstance(a2, A)

    def test_auto_resolve(self):
        a = self.container.resolve(A)
        self.assertIsInstance(a, A)
        
        b = self.container.resolve(B)
        self.assertIsInstance(b, B)
        self.assertIsInstance(b.a, A)

    def test_circular_dependency_patched(self):
        # Using SyncA and SyncB which are patched to have real class annotations
        with self.assertRaises(CircularDependencyError):
            self.container.resolve(SyncA)

    def test_default_value(self):
        # This is expected to fail with the current implementation
        try:
            dv = self.container.resolve(DefaultValue)
            self.assertEqual(dv.value, 10)
        except TypeError as e:
            self.fail(f"Default value resolution failed: {e}")

    def test_no_type_hint_error(self):
        with self.assertRaises(TypeError) as cm:
            self.container.resolve(NoTypeHint)
        self.assertIn("missing type hint or default value", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
