---
name: professional-svg-diagram
description: Create or edit polished SVG architecture diagrams, roadmaps, capability maps, decision flows, and executive report visuals. Use when the requested deliverable is an editable SVG; do not activate for Mermaid-only or raster-image requests.
---

# Professional SVG Report Diagram

## Outcome

Create an editable, executive-ready SVG with a clear reading path, restrained semantic color, concise labels, and enough context to support a verbal walkthrough. Preserve accepted terminology and facts from the user's source material.

If the user explicitly wants Markdown or Mermaid first, produce that intermediate artifact and convert it after the structure is approved, or in the same turn when the user requested both deliverables. Do not replace a requested SVG with Mermaid.

## Choose the Layout First

Identify the information shape before drawing. Use the matching starter only when it fits; do not force content into a template.

| Information shape | Preferred layout | Starter asset |
| --- | --- | --- |
| Source, processing, output, or stacked dependencies | Layered flow | `assets/report-diagram-template.svg` |
| Ownership or execution context across systems | Swimlanes | `assets/swimlane-template.svg` |
| Phased delivery, maturity, or rollout | Timeline | `assets/timeline-template.svg` |
| Capabilities, priorities, or tradeoffs | Matrix | `assets/matrix-template.svg` |
| Rules, routing, validation, or fallback | Decision flow | `assets/decision-flow-template.svg` |

For split comparisons, vertical spines, and hub-and-spoke views, adapt the closest starter or create a purpose-built layout. A top/middle/bottom architecture is appropriate only when it reveals the real dependency shape.

## Visual System

- Choose the canvas from the content. Use `1920x1080` for slide summaries and `1920x1280` to `1920x1600` for deeper flows. Use a wider or taller canvas only when the reading path benefits.
- Use a white page background, pale section fills, subtle borders, and cards with `rx=10` to `14`.
- Use `Inter, PingFang SC, Microsoft YaHei, Arial, sans-serif` and keep text editable.
- Use color semantically and consistently: slate or blue for dependencies and infrastructure, orange for active processing, green for retrieval or capability execution, and pink for result assembly or future capabilities.
- Do not rely on color alone. Pair color with labels, position, border style, or connector style.
- Avoid gradients, decorative blobs, illustrations, and heavy shadows. Use at most one subtle shadow definition.
- Prefer Chinese labels for Chinese requests while preserving technical terms, API names, and acronyms. Continue in Traditional Chinese when the source artifact uses it unless the user requests otherwise.

## Text and Geometry

- Make each card answer what problem the component solves, using business or technical language appropriate to the audience.
- Keep titles under 12 Chinese characters and body lines under 22 Chinese characters when practical.
- Use explicit `<tspan>` lines; do not depend on automatic SVG text wrapping or `foreignObject`.
- Keep at least 24 px horizontal card padding and 18 px vertical padding. Use a minimum body size of 13 px and title size of 16 px on a 1920-wide canvas.
- If text does not fit in two or three short lines, enlarge the card or simplify the wording. Do not shrink individual labels below the minimum size.
- Keep repeated cards aligned and equal in height unless hierarchy requires a visible difference.
- Avoid internal class names, enum names, and code-level details unless the user requests an implementation view.

## Connectors

- Draw only the main flow by default. Connectors should explain reading order, not every dependency.
- Route lines around cards with short horizontal, vertical, or orthogonal segments. Do not cross text or pass through nodes.
- Reconsider the layout when a connector becomes a long diagonal or several connectors cross.
- Do not connect capability inventories as if they were processing steps. Use a dashed border or a small dependency label instead.
- Keep arrow markers inside the viewBox and use consistent marker size and stroke width.

## Workflow

1. Determine the diagram type, audience, source of truth, and natural reading path.
2. Inspect relevant code, documents, accepted diagrams, or existing SVG nodes before asserting project facts or editing an artifact.
3. Select the matching starter asset, or create a purpose-built layout when none fits.
4. Draft the SVG with a clear `<defs>` block, one `<title>`, one `<desc>`, grouped sections, editable text, and explicit connectors.
5. Preserve user corrections exactly. Keep later revisions local to the requested content or layout.
6. Validate with the bundled checker:

```bash
python3 scripts/validate_svg.py path/to/diagram.svg
```

7. Render the SVG to PNG or open it in a browser. Inspect the full canvas at presentation size for clipping, overlap, unreadable text, incorrect font fallback, connector collisions, and ambiguous reading order. XML validation alone is not sufficient.

## Delivery

- Deliver the editable `.svg`; provide a `.png` preview when the available renderer supports it or the user requests one.
- Keep all visible content inside the viewBox, including arrowheads and shadows.
- Use a descriptive lowercase filename with hyphens unless the project already has a naming convention.
- Report the output path and the validation performed. State plainly when visual rendering could not be completed.
