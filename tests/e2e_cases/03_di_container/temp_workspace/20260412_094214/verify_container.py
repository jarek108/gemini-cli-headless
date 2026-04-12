
import unittest
from container import DIContainer, CircularDependencyError

class TestDIContainer(unittest.TestCase):
    def test_singleton(self):
        container = DIContainer()
        class A: pass
        instance = A()
        container.register_singleton(A, instance)
        self.assertIs(container.resolve(A), instance)
        self.assertIs(container.resolve(A), instance)

    def test_factory(self):
        container = DIContainer()
        class A: pass
        container.register_factory(A, lambda: A())
        instance1 = container.resolve(A)
        instance2 = container.resolve(A)
        self.assertIsNot(instance1, instance2)
        self.assertIsInstance(instance1, A)
        self.assertIsInstance(instance2, A)

    def test_auto_resolve_simple(self):
        container = DIContainer()
        class B: pass
        class A:
            def __init__(self, b: B):
                self.b = b
        
        a = container.resolve(A)
        self.assertIsInstance(a, A)
        self.assertIsInstance(a.b, B)

    def test_auto_resolve_nested(self):
        container = DIContainer()
        class C: pass
        class B:
            def __init__(self, c: C):
                self.c = c
        class A:
            def __init__(self, b: B):
                self.b = b
        
        a = container.resolve(A)
        self.assertIsInstance(a, A)
        self.assertIsInstance(a.b, B)
        self.assertIsInstance(a.b.c, C)

    def test_circular_dependency_direct(self):
        container = DIContainer()
        # Define classes that refer to each other by name
        class A:
            def __init__(self, b: 'B'):
                self.b = b
        class B:
            def __init__(self, a: 'A'):
                self.a = a
        
        # We must tell the container where to find 'A' and 'B'
        container.add_scope(locals())
        
        with self.assertRaises(CircularDependencyError):
            container.resolve(A)

    def test_circular_dependency_indirect(self):
        container = DIContainer()
        class A:
            def __init__(self, b: 'B'):
                self.b = b
        class B:
            def __init__(self, c: 'C'):
                self.c = c
        class C:
            def __init__(self, a: 'A'):
                self.a = a
        
        container.add_scope(locals())
        
        with self.assertRaises(CircularDependencyError):
            container.resolve(A)

    def test_missing_type_hint(self):
        container = DIContainer()
        class A:
            def __init__(self, b):
                self.b = b
        
        with self.assertRaisesRegex(NotImplementedError, "Parameter 'b' in 'A' lacks a type hint"):
            container.resolve(A)

if __name__ == '__main__':
    unittest.main()
