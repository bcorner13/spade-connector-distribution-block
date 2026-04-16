#!/usr/bin/env python3
"""
export_stl.py
Export Distribution_Block, Lid, and Mount bodies to files/*.stl via FreeCAD MCP.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_client import mcp  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent
FILES_DIR = PROJECT_ROOT / "files"

EXPORTS = [
    ("Distribution_Block", "Body",         "Distribution_Block.stl"),
    ("Lid",                "Body",         "Lid.stl"),
    ("Mount",              "Body_Bracket", "Mount_Bracket.stl"),
    ("Mount",              "Body_Posts",   "Mount_Posts.stl"),
]

FAILURES = []


def export_stl(doc_name: str, obj_name: str, out_path: Path):
    script = f"""
import FreeCAD, Mesh
doc = FreeCAD.getDocument("{doc_name}")
obj = doc.getObject("{obj_name}")
mesh = doc.addObject("Mesh::Feature", "_export_mesh")
mesh.Mesh = Mesh.Mesh(obj.Shape.tessellate(0.1))
Mesh.export([mesh], "{out_path.as_posix()}")
doc.removeObject("_export_mesh")
"""
    mcp("execute_script", {"script": script})


def main():
    print("=== export_stl ===")
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    for doc_name, obj_name, filename in EXPORTS:
        out = FILES_DIR / filename
        print(f"  Exporting {doc_name}/{obj_name} -> {out.name} ...", end=" ", flush=True)
        try:
            export_stl(doc_name, obj_name, out)
            if out.exists() and out.stat().st_size > 0:
                print(f"ok ({out.stat().st_size // 1024}kB)")
            else:
                FAILURES.append(f"{doc_name}: output file missing or empty")
                print("FAIL (file empty or missing)")
        except Exception as e:
            FAILURES.append(f"{doc_name}: {e}")
            print(f"FAIL ({e})")

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)} issues):")
        for f_ in FAILURES:
            print(f"  - {f_}")
        sys.exit(1)
    else:
        print("PASS: all STL exports completed")


if __name__ == "__main__":
    main()
