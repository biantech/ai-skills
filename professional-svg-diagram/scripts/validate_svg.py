#!/usr/bin/env python3
"""Validate structural invariants for an editable report SVG."""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


URL_REFERENCE = re.compile(r"url\(#([^)]+)\)")
NUMERIC_ATTRIBUTES = {
    "rect": ("x", "y", "width", "height"),
    "line": ("x1", "y1", "x2", "y2"),
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "text": ("x", "y"),
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_number(value: str) -> float:
    match = re.fullmatch(r"\s*(-?(?:\d+(?:\.\d*)?|\.\d+))(?:px)?\s*", value)
    if not match:
        raise ValueError(value)
    return float(match.group(1))


def parse_view_box(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox", "")
    parts = raw.replace(",", " ").split()
    if len(parts) != 4:
        raise ValueError("root viewBox must contain four numbers")
    values = tuple(float(part) for part in parts)
    if values[2] <= 0 or values[3] <= 0:
        raise ValueError("viewBox width and height must be positive")
    return values


def validate_bounds(
    element: ET.Element,
    view_box: tuple[float, float, float, float],
) -> list[str]:
    name = local_name(element.tag)
    required = NUMERIC_ATTRIBUTES.get(name)
    if not required or not all(attribute in element.attrib for attribute in required):
        return []

    try:
        values = {attribute: parse_number(element.attrib[attribute]) for attribute in required}
    except ValueError:
        return []

    min_x, min_y, width, height = view_box
    max_x = min_x + width
    max_y = min_y + height

    if name == "rect":
        bounds = (values["x"], values["y"], values["x"] + values["width"], values["y"] + values["height"])
    elif name == "line":
        bounds = (
            min(values["x1"], values["x2"]),
            min(values["y1"], values["y2"]),
            max(values["x1"], values["x2"]),
            max(values["y1"], values["y2"]),
        )
    elif name == "circle":
        bounds = (
            values["cx"] - values["r"],
            values["cy"] - values["r"],
            values["cx"] + values["r"],
            values["cy"] + values["r"],
        )
    elif name == "ellipse":
        bounds = (
            values["cx"] - values["rx"],
            values["cy"] - values["ry"],
            values["cx"] + values["rx"],
            values["cy"] + values["ry"],
        )
    else:
        bounds = (values["x"], values["y"], values["x"], values["y"])

    if bounds[0] < min_x or bounds[1] < min_y or bounds[2] > max_x or bounds[3] > max_y:
        element_id = element.get("id", "unnamed")
        return [f"{name} '{element_id}' has base geometry outside the viewBox"]
    return []


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return [f"cannot parse SVG: {exc}"]

    if local_name(root.tag) != "svg":
        return ["root element must be <svg>"]

    try:
        view_box = parse_view_box(root)
    except ValueError as exc:
        return [str(exc)]

    direct_children = [local_name(child.tag) for child in root]
    if direct_children.count("title") != 1:
        errors.append("root must contain exactly one <title>")
    if direct_children.count("desc") != 1:
        errors.append("root must contain exactly one <desc>")

    elements = list(root.iter())
    ids = [element.get("id") for element in elements if element.get("id")]
    duplicate_ids = sorted(element_id for element_id, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate ids: {', '.join(duplicate_ids)}")

    references: set[str] = set()
    for element in elements:
        if local_name(element.tag) == "foreignObject":
            errors.append("foreignObject is not allowed; keep text as editable SVG elements")
        for attribute, value in element.attrib.items():
            references.update(URL_REFERENCE.findall(value))
            if local_name(attribute) == "href" and value.startswith("#"):
                references.add(value[1:])
        errors.extend(validate_bounds(element, view_box))

    unresolved = sorted(references - set(ids))
    if unresolved:
        errors.append(f"unresolved references: {', '.join(unresolved)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path, help="SVG file to validate")
    args = parser.parse_args()

    errors = validate(args.svg)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"SVG validation passed: {args.svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
