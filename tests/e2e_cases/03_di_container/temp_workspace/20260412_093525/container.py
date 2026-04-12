import inspect
from typing import Any, Callable, Dict, Set, Type, TypeVar, get_type_hints

T = TypeVar('T')

class CircularDependencyError(Exception):
    """Raised when a circular dependency is detected in the DI container."""
    pass

class DIContainer:
    def __init__(self):
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._resolving: Set[Type] = set()

    def register_singleton(self, cls: Type[T], instance: T) -> None:
        """Registers an existing object as a singleton for a class."""
        if not isinstance(instance, cls):
            raise TypeError(f"Instance must be of type {cls.__name__}")
        self._singletons[cls] = instance

    def register_factory(self, cls: Type[T], factory_func: Callable[[], T]) -> None:
        """Registers a function that creates a new instance every time it is requested."""
        if not callable(factory_func):
            raise TypeError("factory_func must be callable")
        self._factories[cls] = factory_func

    def resolve(self, cls: Type[T]) -> T:
        """
        Automatically resolve and return an instance of the requested class.
        Handles dependency injection by inspecting __init__ arguments and recursively resolving them.
        Detects and raises CircularDependencyError for cyclic dependencies.
        """
        if cls in self._resolving:
            raise CircularDependencyError(f"Circular dependency detected for {cls.__name__}")

        self._resolving.add(cls)

        try:
            # 1. Check if already resolved as singleton or factory
            if cls in self._singletons:
                return self._singletons[cls]

            if cls in self._factories:
                # A factory creates a new instance each time
                instance = self._factories[cls]()
                return instance

            # 2. Ensure it's a class we can instantiate
            if not inspect.isclass(cls):
                raise TypeError(f"Cannot resolve '{cls}'. It is not a registered type, a factory, or a class.")

            # 3. Inspect constructor for dependencies
            sig = inspect.signature(cls.__init__)
            resolved_args: Dict[str, Any] = {}
            
            # Use get_type_hints to resolve forward references and get actual types
            try:
                hints = get_type_hints(cls, include_extras=True)
            except Exception as e:
                # If get_type_hints fails, we will fall back to param.annotation later
                # For now, we store the error to potentially raise it if no fallback works.
                # This specific error handling might be too broad, but for now, we proceed.
                pass # Suppress specific error and try to rely on param.annotation

            for name, param in sig.parameters.items():
                if name == 'self':
                    continue

                # Get the type hint for the parameter, which will be the resolved type if it was a forward reference.
                dependency_type_hint = hints.get(name) # This is the resolved type or None
                default_value = param.default

                # Fallback to param.annotation if hints.get(name) returned None and param has an annotation
                if dependency_type_hint is None and param.annotation != inspect.Parameter.empty:
                    dependency_type_hint = param.annotation

                if dependency_type_hint is not None:
                    # We have a type hint for this parameter (either direct or resolved forward reference).

                    # Check if the dependency type is registered as a singleton or factory.
                    if dependency_type_hint not in self._singletons and dependency_type_hint not in self._factories:
                        # The type is NOT registered.
                        # QRP #1: If there's a default value, use it instead of trying to resolve unregistered types.
                        if default_value != inspect.Parameter.empty:
                            resolved_args[name] = default_value
                            continue # Move to the next parameter
                        else:
                            # Type is not registered and no default value is provided.
                            # We can only attempt to resolve if it's a class type.
                            if inspect.isclass(dependency_type_hint):
                                resolved_args[name] = self.resolve(dependency_type_hint)
                            else:
                                # It's not a class (e.g., Union, List, primitive without registration) and has no default.
                                raise TypeError(f"Cannot resolve unregistered type '{dependency_type_hint.__name__}' for parameter '{name}' in {cls.__name__}. No default value provided and it's not a resolvable class.")
                    else:
                        # The dependency type IS registered. Resolve it.
                        resolved_args[name] = self.resolve(dependency_type_hint)
                
                elif default_value != inspect.Parameter.empty:
                    # No type hint, but has a default value. Use the default value.
                    resolved_args[name] = default_value
                else:
                    # No type hint AND no default value. This parameter cannot be resolved.
                    raise TypeError(f"Cannot resolve dependency '{name}' for {cls.__name__}: missing type hint or default value.")

            # 4. Instantiate the class with resolved arguments
            instance = cls(**resolved_args)
            
            # 5. Register the newly created instance as a singleton by default
            self._singletons[cls] = instance
            return instance

        finally:
            # Always remove the class from the resolving set, whether successful or not.
            self._resolving.discard(cls)
