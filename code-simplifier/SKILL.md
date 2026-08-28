---
name: code-simplifier
description: Simplify recently modified backend or service code while preserving exact behavior. Use for behavior-preserving refactors and new backend code that should remain direct; reject move-only refactors and abstractions that do not reduce current complexity.
---

# Code Simplifier

## Goal
Make recently modified backend code easier to understand from its entrypoint without changing behavior or creating unnecessary structure.

## Scope and Invariants

- Focus on recently modified code. Treat surrounding code as context unless the user explicitly expands the scope.
- Preserve outputs, side effects, public interfaces, queries, transaction boundaries, persistence semantics, and error propagation.
- Stop when behavior preservation is uncertain.

## Net Complexity Gate

- Prefer a direct change in an existing type.
- A simplification must remove current complexity such as duplicated rules, intermediate state, nesting, branches, parameters, dependencies, reader hops, or stale concepts.
- Moving logic to a new type, reducing line count, or making responsibilities look cleaner does not by itself reduce complexity.
- Before adding a production class, interface, record, enum, wrapper, builder, strategy, or context, compare what it adds with what it removes.
- Reject a single-consumer pass-through abstraction unless it represents a complete existing business boundary and clearly reduces overall cognitive load.
- Preserve abstractions that separate real concerns or make debugging and tracing easier.

## Working Rules

1. Read the entrypoint and the affected responsibility chain.
2. Identify the exact redundancy, state, branch, or naming problem being removed.
3. Make the smallest local change that fixes that problem.
4. Keep control flow direct; avoid dense expressions, nested ternaries, unnecessary `try/catch`, defensive guards, fallback paths, and compatibility layers.
5. Keep names aligned with current behavior and remove only stale code made obsolete by the change.
6. Do not rewrite untouched files, collapse separate concerns, or generalize for hypothetical variants.

## Final Check

- Every changed line belongs to the approved scope.
- Exact behavior and failure semantics remain unchanged.
- Each new production type demonstrates a net reduction in current complexity; otherwise remove it.
- The result is easier to read from the entrypoint and no harder to debug or trace.
- When clarity and brevity conflict, choose clarity.
