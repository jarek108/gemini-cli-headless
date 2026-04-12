import inspect
import sys

class CircularDependencyError(Exception):
    pass

class DIContainer:
    def __init__(self):
        self._singletons = {}
        self._factories = {}
        self._resolving = set() # To detect circular dependencies

    def register_singleton(self, cls, instance):
        if not isinstance(instance, cls):
            raise TypeError(f"Instance must be of type {cls.__name__}")
        self._singletons[cls] = instance

    def register_factory(self, cls, factory_func):
        if not callable(factory_func):
            raise TypeError("factory_func must be callable")
        self._factories[cls] = factory_func

    def _resolve_type(self, type_hint, context_cls, caller_locals=None):
        """Resolves a type hint (which can be a class, string, or other type) into a class object."""
        if isinstance(type_hint, str):
            try:
                # Combine global and local scopes for evaluation.
                # Locals from the caller of resolve() are more likely to contain class definitions.
                combined_scope = {} 
                combined_scope.update(globals())
                if caller_locals: # Add locals passed from resolve()
                    combined_scope.update(caller_locals)

                return eval(type_hint, combined_scope)
            except (KeyError, NameError) as e:
                raise NotImplementedError(f"Could not resolve string type annotation '{type_hint}' for parameter in {context_cls.__name__}. Ensure it is a defined class name available in the scope. Error: {e}")
            except Exception as e:
                raise RuntimeError(f"An unexpected error occurred resolving type hint '{type_hint}': {e}")
        elif inspect.isclass(type_hint):
            return type_hint
        else:
            # Handle other type hint scenarios if necessary.
            raise TypeError(f"Unsupported type hint: {type_hint}. Expected a class or a string class name.")

    def resolve(self, cls_or_str, caller_locals=None):
        # Resolve the initial type if it's a string
        if isinstance(cls_or_str, str):
            try:
                # Combine global and local scopes for evaluation.
                combined_scope = {} 
                combined_scope.update(globals())
                if caller_locals: # Add locals passed from the initial call to resolve()
                    combined_scope.update(caller_locals)
                
                cls = eval(cls_or_str, combined_scope)

            except (KeyError, NameError) as e:
                raise NotImplementedError(f"Could not resolve initial type string '{cls_or_str}'. Ensure it is a defined class name available in the scope. Error: {e}")
            except Exception as e:
                raise RuntimeError(f"An unexpected error occurred resolving initial type '{cls_or_str}': {e}")
        elif inspect.isclass(cls_or_str):
            cls = cls_or_str
        else:
            raise TypeError(f"Invalid type provided to resolve: {cls_or_str}. Expected a class or a string class name.")

        if cls in self._resolving:
            # Using cls.__name__ here is safe because cls is guaranteed to be a class object by this point.
            raise CircularDependencyError(f"Circular dependency detected for {cls.__name__}")

        self._resolving.add(cls)

        try:
            # Check for registered singletons
            if cls in self._singletons:
                return self._singletons[cls]

            # Check for registered factories
            if cls in self._factories:
                factory_func = self._factories[cls]
                # Note: A more advanced DI could resolve dependencies *for* the factory_func itself if it had parameters.
                # For this problem, we assume factories are simple and don't take container-resolved args.
                instance = factory_func()
                return instance

            # Auto-resolve by inspecting __init__
            sig = inspect.signature(cls.__init__)
            dependencies = {}
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue

                dep_cls_annotation = param.annotation
                if dep_cls_annotation is inspect.Parameter.empty:
                    # If no annotation, we cannot auto-resolve based on current rules.
                    raise NotImplementedError(f"Auto-resolution for '{name}' in {cls.__name__} requires a type annotation.")

                # Resolve the dependency type using the helper
                # Pass the caller_locals from this resolve() call to _resolve_type
                resolved_dep_cls = self._resolve_type(dep_cls_annotation, cls, caller_locals=sys._getframe(1).f_locals) 
                dependencies[name] = self.resolve(resolved_dep_cls, caller_locals=sys._getframe(1).f_locals) # Pass locals for recursive calls too

            instance = cls(**dependencies)
            return instance

        finally:
            self._resolving.remove(cls)

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Define some classes for testing
    class A:
        def __init__(self):
            pass

    class B:
        def __init__(self, a: A):
            self.a = a

    class C:
        def __init__(self, b: B):
            self.b = b

    class D:
        def __init__(self):
            pass

    # Test case 1: Simple resolution
    print("--- Test Case 1: Simple Resolution ---")
    container1 = DIContainer()
    try:
        instance_a = container1.resolve(A)
        print(f"Resolved A: {instance_a}")
        instance_d = container1.resolve(D)
        print(f"Resolved D: {instance_d}")
    except Exception as e:
        print(f"Error: {e}")

    # Test case 2: Dependency resolution
    print("
--- Test Case 2: Dependency Resolution ---")
    container2 = DIContainer()
    try:
        instance_c = container2.resolve(C)
        print(f"Resolved C: {instance_c}")
        print(f"C.b is instance of B: {isinstance(instance_c.b, B)}")
        print(f"C.b.a is instance of A: {isinstance(instance_c.b.a, A)}")
    except Exception as e:
        print(f"Error: {e}")

    # Test case 3: Singleton registration and resolution
    print("
--- Test Case 3: Singleton Registration ---")
    container3 = DIContainer()
    singleton_a = A()
    container3.register_singleton(A, singleton_a)
    try:
        resolved_a1 = container3.resolve(A)
        resolved_a2 = container3.resolve(A)
        print(f"Resolved A (1st time): {resolved_a1}")
        print(f"Resolved A (2nd time): {resolved_a2}")
        print(f"Are they the same instance? {resolved_a1 is resolved_a2}")
        print(f"Is it the registered singleton? {resolved_a1 is singleton_a}")
    except Exception as e:
        print(f"Error: {e}")

    # Test case 4: Factory registration and resolution
    print("
--- Test Case 4: Factory Registration ---")
    container4 = DIContainer()
    counter = 0
    def create_d():
        nonlocal counter
        counter += 1
        print(f"Factory 'create_d' called (call #{counter})")
        return D()

    container4.register_factory(D, create_d)
    try:
        resolved_d1 = container4.resolve(D)
        resolved_d2 = container4.resolve(D)
        print(f"Resolved D (1st time): {resolved_d1}")
        print(f"Resolved D (2nd time): {resolved_d2}")
        print(f"Are they the same instance? {resolved_d1 is resolved_d2}") # Should be False for factories
    except Exception as e:
        print(f"Error: {e}")

    # Test case 5: Circular dependency
    print("
--- Test Case 5: Circular Dependency ---")
    class X:
        def __init__(self, y: 'Y'): # Using string literal for forward reference
            self.y = y

    class Y:
        def __init__(self, x: X): # Direct class reference
            self.x = x

    container5 = DIContainer()
    try:
        container5.resolve(X)
    except CircularDependencyError as e:
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"Caught unexpected error: {e}")

    # Test case 6: Mixed dependencies (singleton, auto-resolve)
    print("
--- Test Case 6: Mixed Dependencies ---")
    container6 = DIContainer()
    singleton_d = D()
    container6.register_singleton(D, singleton_d)

    # Register A as a singleton to ensure it's used by B if B is resolved by C
    container6.register_singleton(A, A())

    try:
        # C needs B, B needs A. A is a singleton. D is a singleton.
        instance_c_mixed = container6.resolve(C)
        print(f"Resolved C (mixed): {instance_c_mixed}")
        print(f"C.b is instance of B: {isinstance(instance_c_mixed.b, B)}")
        print(f"C.b.a is instance of A: {isinstance(instance_c_mixed.b.a, A)}")
        print(f"Is C.b.a the registered singleton A? {instance_c_mixed.b.a is container6._singletons.get(A)}")
    except Exception as e:
        print(f"Error: {e}")

    # Test case 7: Auto-resolution without type hints (should fail)
    print("
--- Test Case 7: Auto-resolution without type hints (expect failure) ---")
    class E:
        def __init__(self, arg1, arg2): # No type hints
            self.arg1 = arg1
            self.arg2 = arg2
    
    container7 = DIContainer()
    try:
        container7.resolve(E)
    except NotImplementedError as e:
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"Caught unexpected error: {e}")
