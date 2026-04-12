
import unittest
from container import DIContainer

class TestDefaultBehavior(unittest.TestCase):
    def test_auto_resolve_is_singleton(self):
        container = DIContainer()
        class A: pass
        instance1 = container.resolve(A)
        instance2 = container.resolve(A)
        # Check if they are the same
        print(f"Same instance: {instance1 is instance2}")

if __name__ == "__main__":
    unittest.main()
