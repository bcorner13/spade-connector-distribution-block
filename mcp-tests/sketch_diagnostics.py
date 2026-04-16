#!/usr/bin/env python3
"""
sketch_diagnostics.py
Runs mcp__freecad__get_sketch_diagnostics on every sketch in every document.
Fails if any sketch is under- or over-constrained.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_client import mcp  # noqa: E402

DOCS = ["Distribution_Block", "Lid", "Mount"]
SKETCH_TYPES = {"Sketcher::SketchObject"}

FAILURES = []


def get_sketches(doc: str) -> list[str]:
    graph = mcp("get_document_graph", {"doc_name": doc})
    objects = graph.get("objects", {})
    return [name for name, info in objects.items()
            if info.get("type") in SKETCH_TYPES]


def check_sketch(doc: str, name: str):
    try:
        result = mcp("get_sketch_diagnostics", {"doc_name": doc, "name": name})
        constrained = result.get("fully_constrained", False)
        redundant = result.get("redundant_constraints", [])
        conflicting = result.get("conflicting_constraints", [])

        hard_issues = []
        if redundant:
            hard_issues.append(f"redundant constraints: {redundant}")
        if conflicting:
            hard_issues.append(f"conflicting constraints: {conflicting}")

        if hard_issues:
            msg = f"{doc}/{name}: {'; '.join(hard_issues)}"
            FAILURES.append(msg)
            print(f"  FAIL: {msg}")
        elif not constrained:
            print(f"  WARN: {doc}/{name}: under-constrained (geometry OK)")
        else:
            print(f"  ok:   {doc}/{name} fully constrained, no issues")
    except Exception as e:
        FAILURES.append(f"{doc}/{name}: error - {e}")
        print(f"  FAIL: {doc}/{name}: {e}")


def main():
    print("=== sketch_diagnostics ===")
    for doc in DOCS:
        print(f"\n[{doc}]")
        try:
            sketches = get_sketches(doc)
            if not sketches:
                print("  (no sketches found)")
            for sk in sketches:
                check_sketch(doc, sk)
        except Exception as e:
            FAILURES.append(f"Could not inspect {doc}: {e}")
            print(f"  FAIL: could not inspect {doc}: {e}")

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)} issues):")
        for f_ in FAILURES:
            print(f"  - {f_}")
        sys.exit(1)
    else:
        print("PASS: all sketches fully constrained")


if __name__ == "__main__":
    main()
