---
name: enforce-type-annotations
description: Use when writing or refactoring Python code to ensure all public functions have complete type hints.
---
1. Identify all public functions in the code (functions whose names do not start with an underscore).
2. For each public function, verify that every parameter has a type annotation.
3. Verify that the function’s return type is annotated.
4. If any annotation is missing, add it based on the function’s expected input and output types.
5. Use consistent and clear type hints (e.g., built-in types, typing module types).
6. Run static type checkers (e.g., mypy) to confirm annotations are correct and complete.
7. Review docstrings to ensure they align with the type hints.
Self-check:
- Are all public functions fully annotated on parameters and return values?
- Do type hints match the function’s behavior and documentation?
- Does the code pass static type checks without errors?
