class CircularDependencyError(Exception):
    """Custom exception for circular dependencies."""
    pass

class DIContainer:
    def __init__(self):
        self._singletons = {}
        self._factories = {}
        self._resolving = set() # To detect circular dependencies

    def register_singleton(self, cls, instance):
        """Register an existing object as a singleton for a class."""
        if not isinstance(instance, cls):
            raise TypeError(f"Provided instance is not of type {cls.__name__}")
        self._singletons[cls] = instance

    def register_factory(self, cls, factory_func):
        """Register a function that creates a new instance every time it is requested."""
        if not callable(factory_func):
            raise TypeError("Provided factory must be callable")
        self._factories[cls] = factory_func

    def resolve(self, cls):
        """Automatically resolve and return an instance of the requested class."""
        if cls in self._singletons:
            return self._singletons[cls]

        if cls in self._factories:
            # For factories, we still need to ensure dependencies are resolved for the factory itself if it needs them, 
            # and potentially for the instance it creates if that creation process is complex and involves injection.
            # For now, assume factory_func is responsible for its own dependencies or doesn't need injection.
            # A more advanced container might inject into the factory function itself.
            if cls in self._resolving:
                raise CircularDependencyError(f"Circular dependency detected while resolving factory for {cls.__name__}")
            self._resolving.add(cls)
            try:
                instance = self._factories[cls]()
                # If the created instance needs dependency injection itself, this would be a complex scenario.
                # For this basic implementation, we assume the factory produces a ready-to-use instance.
                # We could potentially re-register it as a singleton if that's desired behavior for factories.
            finally:
                self._resolving.remove(cls)
            return instance

        if cls in self._resolving:
            raise CircularDependencyError(f"Circular dependency detected while resolving {cls.__name__}")
        self._resolving.add(cls)

        try:
            # Inspect __init__ arguments and recursively resolve them
            import inspect
            sig = inspect.signature(cls.__init__)
            dependencies = {}
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue
                # Try to infer the type from the annotation, or fall back to a default if not possible/specified
                # This is a simplification; real-world scenarios might need more complex type resolution
                if param.annotation == inspect.Parameter.empty:
                    # Attempt to infer from parameter name if it matches a common pattern, or raise error if cannot infer
                    # For this exercise, let's assume we can only inject types that are explicitly annotated or that the container can directly resolve.
                    # If we cannot infer, we must raise an error or try a default strategy.
                    # For now, let's assume annotations are required for non-self parameters.
                    raise TypeError(f"Cannot resolve dependencies for {cls.__name__}: Parameter '{name}' has no type annotation.")
                
                # Recursively resolve the dependency type
                dependencies[name] = self.resolve(param.annotation)
            
            instance = cls(**dependencies)
            # Optionally, register the newly created instance as a singleton by default if not a factory
            # self.register_singleton(cls, instance) # Uncomment if new instances should be singletons by default
        except Exception as e:
            # Add context to exceptions during resolution
            raise type(e)(f"Error resolving dependencies for {cls.__name__}: {e}") from e
        finally:
            self._resolving.remove(cls)
            
        return instance

