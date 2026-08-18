"""Check Graphify runtime dependencies without modifying the environment."""

from __future__ import annotations

import argparse
import importlib.util


CORE_MODULES = {
    "networkx": "networkx",
    "graspologic": "graspologic",
    "tree-sitter": "tree_sitter",
    "tree-sitter-python": "tree_sitter_python",
    "tree-sitter-javascript": "tree_sitter_javascript",
    "tree-sitter-typescript": "tree_sitter_typescript",
    "tree-sitter-go": "tree_sitter_go",
    "tree-sitter-rust": "tree_sitter_rust",
    "tree-sitter-java": "tree_sitter_java",
    "tree-sitter-c": "tree_sitter_c",
    "tree-sitter-cpp": "tree_sitter_cpp",
    "tree-sitter-ruby": "tree_sitter_ruby",
    "tree-sitter-c-sharp": "tree_sitter_c_sharp",
    "tree-sitter-kotlin": "tree_sitter_kotlin",
    "tree-sitter-scala": "tree_sitter_scala",
    "tree-sitter-php": "tree_sitter_php",
}

OPTIONAL_MODULES = {
    "mcp": {"mcp": "mcp"},
    "neo4j": {"neo4j": "neo4j"},
    "pdf": {"pypdf": "pypdf", "html2text": "html2text"},
    "watch": {"watchdog": "watchdog"},
}


def missing(packages: dict[str, str]) -> list[str]:
    return [
        package
        for package, module in packages.items()
        if importlib.util.find_spec(module) is None
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feature",
        action="append",
        choices=sorted(OPTIONAL_MODULES),
        default=[],
        help="Also check an optional feature. Repeat for multiple features.",
    )
    args = parser.parse_args()

    missing_core = missing(CORE_MODULES)
    if missing_core:
        print("Missing core dependencies: " + ", ".join(missing_core))
    else:
        print("Core dependencies: OK")

    missing_optional: list[str] = []
    for feature in args.feature:
        feature_missing = missing(OPTIONAL_MODULES[feature])
        missing_optional.extend(feature_missing)
        status = ", ".join(feature_missing) if feature_missing else "OK"
        print(f"Optional feature {feature}: {status}")

    return 1 if missing_core or missing_optional else 0


if __name__ == "__main__":
    raise SystemExit(main())
