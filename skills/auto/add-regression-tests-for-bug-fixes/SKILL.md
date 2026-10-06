---
name: add-regression-tests-for-bug-fixes
description: Use when fixing bugs in code to prevent regressions by adding targeted tests.
---
1. For each bug fixed, write at least one dedicated test function that reproduces the bug scenario.
2. Place all regression tests in a designated test file (e.g., tests/test_regressions.py).
3. Ensure each test is independent, clear, and checks the exact behavior that was broken.
4. Run the full test suite to confirm the new tests fail before the fix and pass after.
5. Include edge cases and typical inputs related to the bug.
6. Use assert statements to verify expected outputs precisely.
7. Maintain the regression test file by adding new tests for every future bug fix.
Self-check:
- Does the regression test file include one test per fixed bug?
- Do all regression tests pass after the fix?
- Are the tests clear and maintainable for future reference?
