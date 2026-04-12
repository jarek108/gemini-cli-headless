---
id: QRP-v2
outcome: to correct
recipient: Doer
parent_request: IRQ.md
last_implementation_report: IRP-v2
round: 2
---

# Verification Summary
Implementacja `DIContainer` spełnia podstawowe wymagania dotyczące rejestracji singletonów i fabryk oraz zawiera logikę wykrywania cykli. Jednakże, mechanizm `resolve` jest błędny w obsłudze parametrów posiadających jednocześnie podpowiedź typu (type hint) oraz wartość domyślną. Próbuje on wymusić rezolucję typów prymitywnych (np. `int`), co kończy się błędem `TypeError`. Ponadto, brak obsługi stringów w adnotacjach (forward references) utrudnia testowanie i używanie kontenera w rzeczywistych scenariuszach cyklicznych zależności w Pythonie.

# Trajectory & Loop Detection
- Runda 2: Doer zaimplementował brakujące klasy i plik.
- Funkcjonalność `CircularDependencyError` działa poprawnie od strony logicznej (użycie zbioru `_resolving`), ale jest blokowana przez błędy w samej metodzie `resolve`.
- System zbliża się do celu, ale wymaga poprawy odporności mechanizmu inspekcji konstruktorów.

# Identified Issues
1. **Błąd rezolucji parametrów z wartością domyślną**: Gdy parametr ma adnotację (np. `x: int = 10`), kontener próbuje wywołać `resolve(int)`. Ponieważ `int` jest klasą, kontener próbuje ją zainstancjonować, analizując jej `__init__`, co kończy się błędem `TypeError` (brak hintów dla `*args` w `int`). Kontener powinien preferować wartość domyślną, jeśli typ nie jest zarejestrowany lub jest typem wbudowanym/prymitywnym.
2. **Brak obsługi Forward References**: `resolve` rzuca `TypeError`, jeśli napotka string jako adnotację (np. `c: 'ClassName'`). Jest to częsty wzorzec w Pythonie, zwłaszcza przy cyklach.
3. **Agresywne auto-singletony**: Każda klasa rozwiązana automatycznie staje się singletonem. Choć jest to decyzja projektowa wspomniana w IRP, może być ona kontrowersyjna bez jawnej konfiguracji, ale na tym etapie uznaję to za zgodne z "powerful DI" o ile zostanie zachowane.

# Directives for Doer
1. Popraw metodę `resolve` w `container.py`, aby w przypadku parametrów posiadających wartość domyślną (`param.default != inspect.Parameter.empty`), kontener próbował rozwiązać typ tylko wtedy, gdy jest on zarejestrowany (w `_singletons` lub `_factories`). Jeśli nie jest zarejestrowany, powinien użyć wartości domyślnej zamiast próbować auto-instancjonować klasy takie jak `int` czy `str`.
2. Dodaj obsługę forward references (stringów w adnotacjach) lub upewnij się, że `resolve` potrafi je zignorować/obsłużyć, jeśli to możliwe (np. za pomocą `typing.get_type_hints` z odpowiednim contextem, choć proste zignorowanie i użycie defaultu lub rzucenie czytelniejszego błędu też jest opcją - najlepiej jednak umożliwić rezolucję jeśli typ jest już znany).
3. Upewnij się, że test `test_circular_dependency` (np. A -> B -> A) przechodzi poprawnie przy użyciu standardowych definicji klas.
