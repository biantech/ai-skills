---
name: karpathy-skills-plus
description: "Karpathy's coding guidelines for LLMs, emphasizing simplicity, clarity, and goal-driven execution. Behavioral guidelines to reduce common LLM coding mistakes. Use these principles when writing or modifying code."
license: MIT
---

# Karpathy Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Use these principles when writing or modifying code.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- **State assumptions explicitly.** If uncertain, ask.
- **Present multiple interpretations** if they exist - don't pick silently.
- **Suggest simpler approaches** if they exist. Push back when warranted.
- **If something is unclear, stop.** Name what's confusing. Ask.

### Example Response Pattern

```
Before implementing, I need to clarify:

1. **Scope**: [What's unclear about scope?]
2. **Format**: [What options exist?]
3. **Fields/Data**: [What assumptions would I be making?]
4. **Volume/Scale**: [Does this affect the approach?]

Simplest approach: [Describe simplest solution].
Would need more info for [more complex options].

What's your preference?
```

---

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- ❌ No features beyond what was asked.
- ❌ No abstractions for single-use code.
- ❌ No "flexibility" or "configurability" that wasn't requested.
- ❌ No error handling for impossible scenarios.
- ✅ If you write 200 lines and it could be 50, rewrite it.

**Ask yourself:** "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### When to Add Complexity

| Complexity | Add When |
|------------|----------|
| Caching | When performance actually matters |
| Validation | When bad data actually appears |
| Abstractions | When you actually need multiple types |
| Configuration | When requirements actually vary |

---

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

### When Editing Existing Code

- ❌ Don't "improve" adjacent code, comments, or formatting.
- ❌ Don't refactor things that aren't broken.
- ✅ Match existing style, even if you'd do it differently.
- ✅ If you notice unrelated dead code, mention it - don't delete it.

### When Your Changes Create Orphans

- ✅ Remove imports/variables/functions that YOUR changes made unused.
- ❌ Don't remove pre-existing dead code unless asked.

**The test:** Every changed line should trace directly to the user's request.

---

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

### Transform Tasks into Verifiable Goals

| Vague Request | Verifiable Goal |
|--------------|-----------------|
| "Add validation" | "Write tests for invalid inputs, then make them pass" |
| "Fix the bug" | "Write a test that reproduces it, then make it pass" |
| "Refactor X" | "Ensure tests pass before and after" |

### Multi-Step Plan Format

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

**Strong success criteria** let you loop independently. **Weak criteria** ("make it work") require constant clarification.

---

## Anti-Patterns Quick Reference

| Principle | Anti-Pattern | Fix |
|-----------|-------------|-----|
| Think Before Coding | Silently assumes file format, fields, scope | List assumptions explicitly, ask for clarification |
| Simplicity First | Strategy pattern for single-use case | One function until complexity is actually needed |
| Surgical Changes | Reformats quotes, adds type hints while fixing bug | Only change lines that fix the reported issue |
| Goal-Driven | "I'll review and improve the code" | "Write test for bug X → make it pass → verify no regressions" |

---

## Key Insight

The "overcomplicated" examples aren't obviously wrong—they follow design patterns and best practices. The problem is **timing**: they add complexity before it's needed, which:

- Makes code harder to understand
- Introduces more bugs
- Takes longer to implement
- Harder to test

The "simple" versions are:

- Easier to understand
- Faster to implement
- Easier to test
- Can be refactored later when complexity is actually needed

**Good code is code that solves today's problem simply, not tomorrow's problem prematurely.**

---

## Usage

These guidelines are working if:

- ✅ Fewer unnecessary changes in diffs
- ✅ Fewer rewrites due to overcomplication
- ✅ Clarifying questions come before implementation rather than after mistakes
