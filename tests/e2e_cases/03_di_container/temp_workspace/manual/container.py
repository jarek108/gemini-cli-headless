
import unittest

import inspect

import typing # Import the typing module
from typing import Any, Callable, Type, Dict, Set



class CircularDependencyError(Exception):

    """Raised when a circular dependency is detected."""

    pass



class DIContainer:

    def __init__(self):

        self._singletons: Dict[Type, Any] = {}

        self._factories: Dict[Type, Callable] = {}

        # For cycle detection: stores the classes currently in the resolution stack

        self._resolving_stack: Set[Type] = set()



    def register_singleton(self, cls: Type, instance: Any):

        """Register an existing object as a singleton."""

        if not isinstance(instance, cls):

            raise TypeError(f"Instance of {type(instance)} is not of type {cls.__name__}")

        self._singletons[cls] = instance



    def register_factory(self, cls: Type, factory_func: Callable):

        """Register a function that creates a new instance every time it is requested."""

        if not callable(factory_func):

            raise TypeError("factory_func must be callable")

        # Optional: Add a check to ensure factory_func returns an instance of cls

        self._factories[cls] = factory_func



    def resolve(self, cls: Type) -> Any:

        """Automatically resolve and return an instance of the requested class."""

        if cls in self._resolving_stack:

            # Cycle detected!

            # Construct a more informative error message showing the path

            # (This would require passing the path down, which is more complex.

            # For now, a simple message is sufficient per requirements.)

            raise CircularDependencyError(f"Circular dependency detected for {cls.__name__}")



        self._resolving_stack.add(cls)



        try:

            # 1. Check for registered singletons

            if cls in self._singletons:

                return self._singletons[cls]



            # 2. Check for registered factories

            if cls in self._factories:

                instance = self._factories[cls]()

                # Factories are intended to create new instances each time.

                return instance



            # 3. Auto-resolve if not registered

            # We need to handle cases where cls might be a non-class type or a built-in type.

            # For this problem, we assume cls is a user-defined class.

            

            try:

                sig = inspect.signature(cls.__init__)

            except ValueError: # e.g. for built-in types that don't have inspectable __init__

                 raise TypeError(f"Cannot auto-resolve built-in or uninspectable type: {cls.__name__}")



            dependencies = {}

            

            # Get type hints for the class, resolving forward references.

            # globalns should be the namespace where cls is defined.

            # In this scenario, container.py is imported by test_container.py, and classes

            # are defined in test_container.py. Using globals() from container.py's scope

            # might not resolve types from test_container.py. A more robust approach

            # would be to pass cls.__module__.__dict__ if possible.

            # For now, we'll use globals() and assume it's sufficient for this setup.

            try:
                # Use cls.__init__ to get type hints for the constructor parameters
                type_hints = typing.get_type_hints(cls.__init__)
            except Exception as e:
                # Catch potential errors during type hint resolution
                raise TypeError(f"Error resolving type hints for {cls.__name__}: {e}")



            # Skip 'self' argument

            for name, param in sig.parameters.items():

                if name == 'self':

                    continue

                

                # Check if the parameter has a type hint.

                if param.annotation == inspect.Parameter.empty:

                    raise TypeError(f"Cannot resolve dependency '{name}' for {cls.__name__}: missing type hint.")

                

                # Get the resolved type from type_hints using the parameter name.

                # This will correctly handle string annotations (forward references).

                dependency_type = type_hints.get(name)



                if dependency_type is None:

                    # This could happen if get_type_hints failed to resolve a hint.

                    raise TypeError(f"Could not resolve type hint for dependency '{name}' in {cls.__name__}.")



                # Recursively resolve the dependency

                dependencies[name] = self.resolve(dependency_type)

            

            # Instantiate the class with resolved dependencies

            instance = cls(**dependencies)

            

            # Note: Per requirements, auto-resolved classes are not automatically made singletons.

            # If a class is auto-resolved, subsequent calls to resolve() for that class will re-instantiate it.

            # If implicit singleton behavior is desired, it would need to be explicitly registered or

            # the container would need to cache auto-resolved instances.



            return instance



        finally:

            # Remove from stack after resolution (or error)

            # This ensures the stack is clean for other resolution paths.

            self._resolving_stack.remove(cls)

