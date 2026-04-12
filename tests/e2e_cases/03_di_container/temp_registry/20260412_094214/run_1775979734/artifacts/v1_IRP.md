---
id: IRP-v1
outcome: ready
recipient: QA | Manager
parent_request: IRQ.md
implementing_actor: Doer
implementation_round: 1
last_qa_report: None
---

# Summary
## Context
The task was to implement a Python Dependency Injection (DI) container named `DIContainer`. The container needs to support registering singletons and factories, automatically resolve dependencies by inspecting constructor arguments, and critically, detect and prevent circular dependencies by raising a `CircularDependencyError`. This is the first implementation round.

## Work performed
A Python file `container.py` was created, containing the `CircularDependencyError` exception and the `DIContainer` class. The class implements methods for registering singletons (`register_singleton`) and factories (`register_factory`). The `resolve` method handles dependency resolution by inspecting `__init__` signatures and recursively calling `resolve` for un-registered dependencies, employing a dependency graph to detect circular references. Additionally, the error message for missing type hints in dependency resolution has been improved for better user guidance.

# Guideline realization

## Deviations from IRQ or QA feedback
NONE.

## Failing and changed test rationale
No tests were explicitly requested or implemented in this initial phase. The focus was on setting up the core functionality as described in the IRQ.

# Implementation details

## Design & implementation choices
-   **DIContainer Structure**: Uses dictionaries (`_singletons`, `_factories`) to store registered instances and factories, keyed by class. A `_dependency_graph` dictionary is used to track the current resolution path for cycle detection.
-   **Circular Dependency Detection**: Before resolving a class, it's added to `_dependency_graph`. If `resolve` is called again for a class already in `_dependency_graph`, a `CircularDependencyError` is raised. The class is removed from the graph upon successful instantiation or error during resolution.
-   **Automatic Resolution**: The `resolve` method inspects the `__init__` method's signature using `inspect.signature`. It iterates through parameters that do not have default values.
-   **Dependency Class Inference**: The `_get_dependency_class` method prioritizes type annotations (`param.annotation`). If a type annotation is present, it's used to determine the class to resolve. If no type annotation is found, a `NotImplementedError` is raised with a detailed message instructing the user to add type hints and providing an example. This refined error message enhances user experience and clarifies the requirement for explicit type hints in automatic resolution.
-   **Singleton vs. Factory**: Singletons return the same instance every time, while factories create a new instance on each call.

## Files/Modules touched
-   `container.py`: Contains the `CircularDependencyError` and `DIContainer` implementation.
-   `IRQ.md`: Analyzed for requirements.
-   `IRP.md`: Updated to document this implementation.

# Relation to past and future work

## Implementation effort history
This is the first implementation round. No prior attempts were made.

## Open potential follow-ups, TODOs, out of scope items
-   **Comprehensive Unit Tests**: Add a suite of unit tests to cover all functionalities: registration, singleton behavior, factory behavior, simple resolution, nested resolution, and various circular dependency scenarios.
-   **Advanced Dependency Mapping**: Implement a more sophisticated mechanism for mapping constructor parameter names to classes when type hints are absent, perhaps via explicit registration or convention-based lookup beyond basic heuristics.
-   **Error Handling**: Enhance error messages for better debugging.
-   **Scoping**: Implement different scopes (e.g., request scope, session scope) for singletons.
-   **Configuration**: Allow configuration of the container itself.

# Self Assessment

## Edge cases and known limitations
-   **Ambiguous Dependencies**: The current implementation relies heavily on type hints for automatic resolution. If type hints are missing for constructor parameters, resolution will fail with a `NotImplementedError`, but the error message now provides clearer guidance on adding type hints.
-   **No Explicit Mapping**: The container does not currently support explicit mapping of parameter names to specific class instances or factories when type hints are ambiguous or absent.
-   **Performance**: For very deep or complex dependency graphs, the recursive nature of `resolve` might have performance implications, though it is mitigated by caching singletons.
-   **`__init__` only**: Resolution is currently limited to dependencies defined in the `__init__` method. Other methods requiring DI are not supported.

## QA handoff
Actionable validation plan:
1.  **Basic Registration and Resolution**:
    *   Register a simple class as a singleton and resolve it. Verify the same instance is returned on subsequent resolutions.
    *   Register a simple class as a factory and resolve it multiple times. Verify different instances are returned.
    *   Register a class with no dependencies and resolve it.
2.  **Nested Dependencies**:
    *   Create classes A, B, and C where A depends on B, and B depends on C. Register C, then resolve A. Verify A, B, and C are instantiated correctly in the right order.
    *   Register B as a singleton, and A depends on B. Resolve A. Verify A gets the singleton instance of B.
3.  **Circular Dependency Detection**:
    *   Create classes A and B where A depends on B, and B depends on A. Attempt to resolve either A or B.
    *   Verify that a `CircularDependencyError` is raised with an informative message.
    *   Test a three-class circular dependency (A -> B -> C -> A) and ensure it also raises the correct error.
4.  **Type Hint Enforcement (Improved Error Message)**:
    *   Create a class with a constructor parameter lacking a type hint and attempt to resolve it.
    *   Verify that a `NotImplementedError` is raised from `_get_dependency_class`. The error message should be specific, indicating the parameter name, parent class, and guiding the user with an example on how to add the type hint (e.g., `param_name: YourDependencyClass`).
5.  **Error Propagation**: Ensure errors during the instantiation of a dependency propagate correctly up the call stack.
