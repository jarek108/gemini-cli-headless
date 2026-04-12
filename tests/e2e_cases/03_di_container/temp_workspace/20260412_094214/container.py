# Move import inspect to the top
import inspect

class CircularDependencyError(Exception):
    pass

class DIContainer:
    def __init__(self):
        self._singletons = {}
        self._factories = {}
        self._dependency_graph = {}
        # Store global scopes to resolve string forward references.
        # Initialize with the container's own globals().
        self._global_scopes = [globals()]

    def register_singleton(self, cls, instance):
        self._singletons[cls] = instance

    def register_factory(self, cls, factory_func):
        self._factories[cls] = factory_func

    def add_scope(self, scope_globals):
        """Adds a new global scope (e.g., from a module's globals())
        to be used for resolving string forward references.
        """
        self._global_scopes.append(scope_globals)

    def resolve(self, dependency_ref):
        # If the dependency is already registered as a singleton
        if dependency_ref in self._singletons:
            return self._singletons[dependency_ref]

        # If it's a factory
        if dependency_ref in self._factories:
            return self._factories[dependency_ref]()

        # Resolve the class object from the reference (which could be a class or a string)
        cls = dependency_ref
        if isinstance(dependency_ref, str):
            resolved_cls = None
            # Try to resolve the string reference from registered scopes
            for scope in self._global_scopes:
                if dependency_ref in scope:
                    resolved_cls = scope[dependency_ref]
                    break
            
            if resolved_cls is None:
                # If not found in any registered scope, raise an error.
                raise NotImplementedError(f"Cannot resolve string forward reference: '{dependency_ref}'. Class not found in any registered scope.")
            cls = resolved_cls

        # Check for circular dependencies
        if cls in self._dependency_graph:
            raise CircularDependencyError(f"Circular dependency detected when trying to resolve {cls.__name__}.")

        # Mark as visiting
        self._dependency_graph[cls] = None

        try:
            # Inspect constructor arguments using inspect.signature(cls) to skip 'self'
            init_signature = inspect.signature(cls)
            dependencies = {}
            for name, param in init_signature.parameters.items():
                # Only resolve parameters that do not have a default value
                if param.default == inspect.Parameter.empty:
                    # Infer the dependency reference (class or string) using the helper method
                    dependency_cls_ref = self._get_dependency_class(cls, name, param)
                    # Recursively resolve the dependency. If dependency_cls_ref is a string, resolve() will handle it.
                    dependencies[name] = self.resolve(dependency_cls_ref)
                else:
                    # If a parameter has a default value, we don't auto-resolve it.
                    pass
            
            instance = cls(**dependencies)
            self._singletons[cls] = instance
            # Remove from visiting graph upon successful instantiation
            del self._dependency_graph[cls]
            return instance
        except Exception as e:
            # If an error occurs during instantiation, remove from graph to allow retries or other paths
            if cls in self._dependency_graph:
                del self._dependency_graph[cls]
            # Re-raise the exception with more context
            raise type(e)(f"Failed to resolve {cls.__name__}: {e}") from e

    def _get_dependency_class(self, parent_cls, param_name, param):
        """
        Infers the dependency class from parameter annotations or name.
        Returns the dependency reference (which can be a class or a string).
        """
        # 1. Check for explicit type annotation
        if param.annotation != inspect.Parameter.empty:
            dependency_ref = param.annotation
            # 2. If annotation is a string, return it as a reference to be resolved by resolve()
            # 3. If annotation is a class or type, return it directly.
            return dependency_ref
        else:
            # 4. If no annotation, raise an error as per the requirement.
            raise NotImplementedError(f"Parameter '{param_name}' in '{parent_cls.__name__}' lacks a type hint. Automatic dependency resolution requires type hints.")
