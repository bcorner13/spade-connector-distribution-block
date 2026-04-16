#!/usr/bin/env python3
"""
export_mesh.py
Export Distribution_Block, Lid, and Mount bodies to files/*.stl and files/*.3mf
via FreeCAD MCP.  Also produces a combined PowerDistribution.3mf assembly file.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_client import mcp  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent
FILES_DIR = PROJECT_ROOT / "files"

# (doc, object, stem) — exported as both {stem}.stl and {stem}.3mf
PARTS = [
    ("Distribution_Block", "Body",         "Distribution_Block"),
    ("Lid",                "Body",         "Lid"),
    ("Mount",              "Body_Bracket", "Mount_Bracket"),
    ("Mount",              "Body_Posts",   "Mount_Posts"),
]

ASSEMBLY_FILE = "PowerDistribution.3mf"

FAILURES = []


def export_part(doc_name: str, obj_name: str, out_path: Path):
    """Export a single body to STL or 3MF (format chosen by extension)."""
    script = f"""
import FreeCAD, Mesh
doc = FreeCAD.getDocument("{doc_name}")
obj = doc.getObject("{obj_name}")
shape = obj.Tip.Shape if hasattr(obj, 'Tip') and obj.Tip else obj.Shape
mesh = doc.addObject("Mesh::Feature", "_export_mesh")
mesh.Mesh = Mesh.Mesh(shape.tessellate(0.1))
Mesh.export([mesh], "{out_path.as_posix()}")
doc.removeObject("_export_mesh")
"""
    mcp("execute_script", {"script": script})


def export_assembly(parts: list, out_path: Path):
    """Export multiple bodies into a single 3MF with named components."""
    mesh_setup = []
    mesh_names = []
    for doc_name, obj_name, stem in parts:
        safe = stem.replace("-", "_")
        mesh_names.append(safe)
        mesh_setup.append(f"""
obj = FreeCAD.getDocument("{doc_name}").getObject("{obj_name}")
shape = obj.Tip.Shape if hasattr(obj, 'Tip') and obj.Tip else obj.Shape
m_{safe} = scratch.addObject("Mesh::Feature", "{safe}")
m_{safe}.Mesh = Mesh.Mesh(shape.tessellate(0.1))
""")

    export_list = ", ".join(f"m_{n}" for n in mesh_names)
    script = f"""
import FreeCAD, Mesh
scratch = FreeCAD.newDocument("_export_asm")
{''.join(mesh_setup)}
Mesh.export([{export_list}], "{out_path.as_posix()}")
FreeCAD.closeDocument("_export_asm")
"""
    mcp("execute_script", {"script": script})


def check_output(label: str, path: Path) -> bool:
    if path.exists() and path.stat().st_size > 0:
        print(f"ok ({path.stat().st_size // 1024}kB)")
        return True
    else:
        FAILURES.append(f"{label}: output file missing or empty")
        print("FAIL (file empty or missing)")
        return False


def main():
    print("=== export_mesh ===")
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    # Individual parts — STL and 3MF
    for doc_name, obj_name, stem in PARTS:
        for ext in ("stl", "3mf"):
            filename = f"{stem}.{ext}"
            out = FILES_DIR / filename
            print(f"  {doc_name}/{obj_name} -> {filename} ...", end=" ", flush=True)
            try:
                export_part(doc_name, obj_name, out)
                check_output(f"{doc_name}/{obj_name} {ext}", out)
            except Exception as e:
                FAILURES.append(f"{doc_name} {ext}: {e}")
                print(f"FAIL ({e})")

    # Assembly 3MF
    out = FILES_DIR / ASSEMBLY_FILE
    print(f"  Assembly -> {ASSEMBLY_FILE} ...", end=" ", flush=True)
    try:
        export_assembly(PARTS, out)
        check_output("Assembly 3MF", out)
    except Exception as e:
        FAILURES.append(f"Assembly 3MF: {e}")
        print(f"FAIL ({e})")

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)} issues):")
        for f_ in FAILURES:
            print(f"  - {f_}")
        sys.exit(1)
    else:
        print("PASS: all mesh exports completed")


if __name__ == "__main__":
    main()
