# Task: Dependency Injection Container with Cycle Detection

Your goal is to implement a simple but powerful Dependency Injection (DI) container in Python.

### Requirements:
1.  Class Name: `DIContainer`.
2.  Method `register_singleton(cls, instance)`: Register an existing object as a singleton for a class.
3.  Method `register_factory(cls, factory_func)`: Register a function that creates a new instance every time it is requested.
4.  Method `resolve(cls)`: Automatically resolve and return an instance of the requested class.
    - If a singleton/factory is registered, use it.
    - If not, try to instantiate the class by inspecting its `__init__` arguments and recursively resolving them.
5.  **CRITICAL: Circular Dependency Detection**: If a dependency cycle is detected (e.g., A needs B, B needs A), the container must raise a custom exception `CircularDependencyError` instead of entering infinite recursion.
6.  The code should be placed in a file named `container.py`.

### Definition of Done:
- `container.py` contains the class and exception.
- Automatic resolution of constructor arguments works.
- Circular dependencies are detected and raise the correct error.
- An Implementation Report (`vN_IRP.md`) is produced.
