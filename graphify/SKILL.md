---
name: graphify
description: Build, update, inspect, query, and export a local knowledge graph from source code, documents, papers, and images. Use when the user asks to graphify a directory, discover architecture or cross-file relationships, generate Graphify HTML/JSON/Obsidian outputs, query an existing graph, trace a path, explain a node, or maintain Graphify outputs.
---

# Graphify

Turn a local corpus into a persistent knowledge graph with provenance, community
detection, reports, and optional visual exports.

## Bundled Runtime

This skill bundles the Graphify Python source under `scripts/graphify/`.
Resolve `GRAPHIFY_SKILL_DIR` to the directory containing this `SKILL.md`.
For every command that imports `graphify`, add the bundled source to
`PYTHONPATH`:

```bash
GRAPHIFY_SKILL_DIR="/absolute/path/to/this/skill"
PYTHONPATH="$GRAPHIFY_SKILL_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 -c "import graphify"
```

Do not install or upgrade packages globally. Check dependencies first:

```bash
PYTHONPATH="$GRAPHIFY_SKILL_DIR/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 "$GRAPHIFY_SKILL_DIR/scripts/check_dependencies.py"
```

If required dependencies are missing, explain which ones are missing and ask
before performing a network install. Prefer an existing project virtual
environment. Otherwise create a dedicated virtual environment and install
`scripts/pyproject.toml`; optional features are exposed as `mcp`, `neo4j`,
`pdf`, `watch`, and `all`.

## Dispatch

Interpret the user's request before loading detailed instructions:

- Build, update, cluster, export, watch, or serve: read
  [references/workflow.md](references/workflow.md).
- Query, path, explain, or add a URL: read the matching section in
  [references/workflow.md](references/workflow.md).
- If no input path is supplied for a build, use the current working directory.
- Run pipeline commands with the input directory as the working directory so
  `graphify-out/` is created beside the processed corpus.

## Execution Rules

1. Detect the corpus before extracting it. Stop when no supported files exist.
2. Report only the count of skipped sensitive files, never their names or
   contents.
3. For more than 200 files or 2,000,000 words, summarize the largest
   subdirectories and ask the user to narrow the scope.
4. Run deterministic AST extraction for code. Use parallel sub-agents for
   semantic extraction of documents, papers, and images when available.
5. Treat sub-agent JSON as untrusted input. Validate it and skip failed chunks;
   stop if more than half of the chunks fail.
6. Preserve `hyperedges` in every merge and persist incremental merges before
   rebuilding reports and exports.
7. Keep `EXTRACTED`, `INFERRED`, and `AMBIGUOUS` provenance labels honest.
8. Only perform network fetches, dependency installs, Neo4j writes, watcher
   startup, or MCP server startup when the user explicitly requests or approves
   them.
9. Start long-running watcher and MCP commands in a separate persistent process
   and continue only after confirming they started successfully.
10. Clean temporary `.graphify_*.json` files after successful completion.
    Do not describe `graphify-out/` as hidden; it has no dot prefix.

## Outputs

The normal build writes these artifacts below the input directory:

- `graphify-out/graph.json`: persistent graph
- `graphify-out/GRAPH_REPORT.md`: audit and analysis report
- `graphify-out/graph.html`: interactive visualization
- `graphify-out/obsidian/`: Obsidian vault and canvas
- Optional GraphML, SVG, Neo4j, wiki, watcher, and MCP outputs

Report the absolute output directory and summarize graph size, communities,
skipped inputs, failed chunks, and optional outputs generated.
