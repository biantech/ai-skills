---
name: riper-workflow
description: RIPER methodology — Research, Innovate, Plan, Execute, Review. Five-phase systematic development with separation of concerns, persistent artifacts per phase, and approval gates. Use for architecture changes, multi-file refactors, migrations, or any work where mistakes compound.
license: MIT
---

# RIPER workflow

## Phases

1. **Research** — read-only. Output: research-notes.md.
2. **Innovate** — read-only. Output: approaches.md (2-3 viable).
3. **Plan** — write to docs. Output: [task]-plan.md with measurable success criteria.
4. **Execute** — full access. Follow plan, verify each step.
5. **Review** — read-only after. Output: review.md.

## Principles

- Separation of concerns: each phase has its own access mode
- Context efficiency: minimal tokens per phase
- Persistent knowledge: `~/dev/[task]/` per task
- Conscious transitions: deliberate phase changes

## When

Use for architecture, migrations, auth/payments/data work, multi-file refactors.

Don't use for typo fixes, obvious single-file bugs, prototype exploration.

---

Full content + worked task example at https://github.com/biantech/ai-skills/riper-workflow-skills.
