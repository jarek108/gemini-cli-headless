
import unittest
import inspect
from container import DIContainer, CircularDependencyError

# --- Test Classes ---
class ServiceA:
    def __init__(self, service_b: 'ServiceB'):
        self.service_b = service_b

class ServiceB:
    def __init__(self, service_a: 'ServiceA'):
        self.service_a = service_a

class ServiceC:
    def __init__(self, service_d: 'ServiceD'):
        self.service_d = service_d

class ServiceD:
    def __init__(self):
        pass

class ServiceWithFactory:
    def __init__(self, value: str):
        self.value = value

class ServiceWithSingleton:
    def __init__(self, config: 'Config'):
        self.config = config

class Config:
    def __init__(self, setting: str):
        self.setting = setting

class IndirectA:
    def __init__(self, indirect_b: 'IndirectB'):
        self.indirect_b = indirect_b

class IndirectB:
    def __init__(self, indirect_c: 'IndirectC'):
        self.indirect_c = indirect_c

class IndirectC:
    def __init__(self, indirect_a: 'IndirectA'):
        self.indirect_a = indirect_a

# --- Test Cases ---
class TestDIContainer(unittest.TestCase):
    def test_resolve_simple_class(self):
        container = DIContainer()
        instance = container.resolve(ServiceD)
        self.assertIsInstance(instance, ServiceD)

    def test_resolve_with_dependency(self):
        container = DIContainer()
        instance = container.resolve(ServiceC)
        self.assertIsInstance(instance, ServiceC)
        self.assertIsInstance(instance.service_d, ServiceD)

    def test_register_and_resolve_singleton(self):
        container = DIContainer()
        config_instance = Config(setting="prod")
        container.register_singleton(Config, config_instance)
        
        service_instance = container.resolve(ServiceWithSingleton)
        self.assertIsInstance(service_instance, ServiceWithSingleton)
        self.assertIs(service_instance.config, config_instance)
        
        resolved_config = container.resolve(Config)
        self.assertIs(resolved_config, config_instance)

    def test_register_and_resolve_factory(self):
        container = DIContainer()
        
        def create_service_with_factory():
            return ServiceWithFactory(value="factory_created")
        
        container.register_factory(ServiceWithFactory, create_service_with_factory)
        
        instance1 = container.resolve(ServiceWithFactory)
        instance2 = container.resolve(ServiceWithFactory)
        
        self.assertIsInstance(instance1, ServiceWithFactory)
        self.assertEqual(instance1.value, "factory_created")
        
        self.assertIsInstance(instance2, ServiceWithFactory)
        self.assertEqual(instance2.value, "factory_created")
        
        self.assertIsNot(instance1, instance2)

    def test_circular_dependency_direct(self):
        container = DIContainer()
        with self.assertRaises(CircularDependencyError):
            container.resolve(ServiceA)

    def test_circular_dependency_indirect(self):
        container = DIContainer()
        with self.assertRaises(CircularDependencyError):
            container.resolve(IndirectA)
            
    def test_dependency_with_missing_type_hint(self):
        class ServiceWithoutHint:
            def __init__(self, missing_arg):
                self.missing_arg = missing_arg
        
        container = DIContainer()
        with self.assertRaisesRegex(TypeError, "missing type hint"):
            container.resolve(ServiceWithoutHint)

if __name__ == '__main__':
    unittest.main()
