# ai-skills

A curated collection of reusable skills for coding agents. Each skill lives in its own directory and includes a `SKILL.md` with activation rules, workflow, and safety boundaries.

## Skills

### Coding quality

| Skill | Summary |
| --- | --- |
| [karpathy-guidelines](andrej-karpathy-skills/karpathy-guidelines/) | Behavioral guidelines for simple, surgical, assumption-aware LLM coding. |
| [karpathy-skills-plus](karpathy-skills-plus/) | Karpathy-inspired principles for clear, goal-driven implementation. |
| [code-simplifier](code-simplifier/) | Simplify recently changed backend code while preserving exact behavior. |
| [ponytail](ponytail/) | Choose the smallest working solution and avoid unnecessary abstractions or dependencies. |

### Debugging, operations, and data

| Skill | Summary |
| --- | --- |
| [fact-first-diagnose](fact-first-diagnose/) | Separate code-proven conclusions from runtime-dependent hypotheses during diagnosis. |
| [minimal-query-planner](minimal-query-planner/) | Plan selective, bounded, read-only queries with explicit cost and safety limits. |
| [data-knowledge-capture](data-knowledge-capture/) | Preserve reusable, sanitized data workflows, schemas, rules, and validation knowledge. |
| [db-tools](db-tools/) | Required helper for ground-truth live-data queries across Yuanchuan services. |
| [azure-appinsights-query](azure-appinsights-query/) | Run bounded read-only KQL investigations against configured UAT, RC, or Prod resources. |
| [kuboard-log](kuboard-log/) | Inspect Kubernetes workloads and bounded container logs through Kuboard. |
| [gateway-api-debug](gateway-api-debug/) | Validate gateway routes and make bounded end-to-end API calls in an approved environment. |
| [jenkins-api-build](jenkins-api-build/) | Inspect, trigger, and track configured Jenkins Dev, UAT, and RC jobs. |

### Workflows and developer tools

| Skill | Summary |
| --- | --- |
| [riper](riper/) | Explicit five-phase RIPER workflow for complex engineering tasks. |
| [riper-workflow](riper-workflow/) | Research, Innovate, Plan, Execute, and Review with persistent phase artifacts. |
| [planning-with-files](planning-with-files/) | Maintain durable Markdown plans and progress files for multi-step work. |
| [find-skills](find-skills/) | Help users discover and install skills matching a requested capability. |
| [graphify](graphify/) | Build, query, inspect, and export a local knowledge graph from source material. |
| [playwright](playwright/) | Automate a real browser from the terminal with `playwright-cli`. |

### Content and visual creation

| Skill | Summary |
| --- | --- |
| [gaokao-essay-coach](gaokao-essay-coach/) | Coach Chinese high-school exam essays through prompt analysis, drafting, revision, and scoring. |
| [pdf](pdf/) | Read, create, and review PDFs with text extraction and rendered-layout verification. |
| [professional-svg-diagram](professional-svg-diagram/) | Create polished, editable SVG diagrams for architecture, roadmaps, and executive reports. |
| [hatch-pet](hatch-pet/) | Create, repair, validate, and package animated Codex-compatible pets and spritesheets. |
| [caveman](caveman/) | Switch to an intentionally terse communication style with configurable intensity. |

## Usage

Install or copy a skill directory into the agent's skills location, then invoke it according to its `SKILL.md`. Some skills are automatic for matching tasks; others require an explicit request such as `$riper` or `caveman mode`. Always read the skill's instructions before use, especially for live systems and external services.

## Repository layout

- `SKILL.md`: canonical instructions and trigger conditions.
- `SKILL_zh.md` or `skill-zh.md`: Chinese documentation when available.
- `agents/`, `scripts/`, `references/`, `assets/`, and `tests/`: optional supporting resources.

## License

See the license files in this repository and in individual skill directories.
