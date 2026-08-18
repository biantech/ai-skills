"""Graphify command-line helpers bundled with the Codex skill."""

from __future__ import annotations

import json
import sys
from pathlib import Path


_PROJECT_INSTRUCTIONS = """\
## graphify knowledge graph

This project has a Graphify knowledge graph at graphify-out/.

- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md.
- If graphify-out/wiki/index.md exists, navigate it before scanning the raw graph JSON.
- After modifying code, rebuild the graph so generated outputs stay current.
"""


def vscode_install(project_dir: Path | None = None) -> None:
    """Write Graphify context to GitHub Copilot project instructions."""
    base = (project_dir or Path(".")).resolve()
    github_dir = base / ".github"
    github_dir.mkdir(exist_ok=True)
    target = github_dir / "copilot-instructions.md"

    if target.exists():
        content = target.read_text()
        if "## graphify knowledge graph" in content:
            print("Graphify is already configured in copilot-instructions.md")
            return
        target.write_text(content.rstrip() + "\n\n" + _PROJECT_INSTRUCTIONS)
    else:
        target.write_text(_PROJECT_INSTRUCTIONS)
    print(f"Graphify instructions written to {target}")


def _print_help() -> None:
    print("Usage: graphify <command>")
    print()
    print("Commands:")
    print("  benchmark [graph.json]  measure token reduction")
    print("  hook install            install the post-commit rebuild hook")
    print("  hook uninstall          remove the post-commit rebuild hook")
    print("  hook status             check hook status")
    print("  vscode install          write GitHub Copilot project instructions")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        _print_help()
        return

    command = sys.argv[1]
    if command == "vscode":
        if len(sys.argv) > 2 and sys.argv[2] == "install":
            vscode_install()
            return
        print("Usage: graphify vscode install", file=sys.stderr)
        raise SystemExit(1)

    if command == "hook":
        from graphify.hooks import install, status, uninstall

        subcommand = sys.argv[2] if len(sys.argv) > 2 else ""
        handlers = {"install": install, "uninstall": uninstall, "status": status}
        handler = handlers.get(subcommand)
        if handler is None:
            print("Usage: graphify hook [install|uninstall|status]", file=sys.stderr)
            raise SystemExit(1)
        print(handler(Path(".")))
        return

    if command == "benchmark":
        from graphify.benchmark import print_benchmark, run_benchmark

        graph_path = sys.argv[2] if len(sys.argv) > 2 else "graphify-out/graph.json"
        corpus_words = None
        detect_path = Path(".graphify_detect.json")
        if detect_path.exists():
            try:
                corpus_words = json.loads(detect_path.read_text()).get("total_words")
            except (json.JSONDecodeError, OSError):
                pass
        print_benchmark(run_benchmark(graph_path, corpus_words=corpus_words))
        return

    print(f"error: unknown command '{command}'", file=sys.stderr)
    _print_help()
    raise SystemExit(1)


if __name__ == "__main__":
    main()
