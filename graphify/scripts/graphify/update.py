"""Helpers for persisting an incremental Graphify merge."""

from __future__ import annotations

import json
from pathlib import Path

from networkx.readwrite import json_graph

from .build import build_from_json


def _graph_to_extraction(graph) -> dict:
    nodes = [{"id": node_id, **attrs} for node_id, attrs in graph.nodes(data=True)]
    edges = []
    for source, target, attrs in graph.edges(data=True):
        edge = {
            "source": attrs.get("_src", source),
            "target": attrs.get("_tgt", target),
            **{k: v for k, v in attrs.items() if k not in {"_src", "_tgt"}},
        }
        edges.append(edge)
    return {
        "nodes": nodes,
        "edges": edges,
        "hyperedges": graph.graph.get("hyperedges", []),
        "input_tokens": graph.graph.get("input_tokens", 0),
        "output_tokens": graph.graph.get("output_tokens", 0),
    }


def merge_incremental(
    existing_graph_path: str | Path,
    new_extraction_path: str | Path,
    output_path: str | Path,
) -> dict:
    """Merge a new extraction into an existing graph and persist extraction JSON."""
    existing_data = json.loads(Path(existing_graph_path).read_text())
    existing_graph = json_graph.node_link_graph(existing_data, edges="links")
    existing_graph.graph["hyperedges"] = existing_data.get(
        "hyperedges", existing_graph.graph.get("hyperedges", [])
    )

    new_extraction = json.loads(Path(new_extraction_path).read_text())
    new_graph = build_from_json(new_extraction)
    old_hyperedges = list(existing_graph.graph.get("hyperedges", []))
    existing_graph.update(new_graph)

    merged_hyperedges = []
    seen_ids = set()
    for hyperedge in old_hyperedges + new_extraction.get("hyperedges", []):
        hyperedge_id = hyperedge.get("id")
        if hyperedge_id and hyperedge_id not in seen_ids:
            seen_ids.add(hyperedge_id)
            merged_hyperedges.append(hyperedge)
    existing_graph.graph["hyperedges"] = merged_hyperedges
    existing_graph.graph["input_tokens"] = new_extraction.get("input_tokens", 0)
    existing_graph.graph["output_tokens"] = new_extraction.get("output_tokens", 0)

    extraction = _graph_to_extraction(existing_graph)
    Path(output_path).write_text(json.dumps(extraction, indent=2))
    return extraction
