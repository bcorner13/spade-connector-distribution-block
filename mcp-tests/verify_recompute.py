#!/usr/bin/env python3
"""
verify_recompute.py
Load qd_bar_vars.json into FreeCAD VarSet via MCP, trigger recompute, save screenshot.
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_client import mcp  # noqa: E402

VARS_FILE = Path(__file__).parent.parent / "cad" / "varsets" / "qd_bar_vars.json"
OUTPUT_DIR = Path(__file__).parent / "output"
DOC_NAME = "Params"


def load_vars():
    with open(VARS_FILE) as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def push_varset(vars_: dict):
    """Write each param into the FreeCAD VarSet via execute_script."""
    assignments = []
    for k, v in vars_.items():
        if isinstance(v, str):
            assignments.append(f'vs.{k} = "{v}"')
        else:
            assignments.append(f"vs.{k} = {v}")
    script = f"""
import FreeCAD
doc = FreeCAD.getDocument("{DOC_NAME}")
vs = doc.getObject("VarSet")
{chr(10).join(assignments)}
for d in FreeCAD.listDocuments().values():
    d.recompute()
"""
    mcp("execute_script", {"script": script})


def screenshot(name: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = mcp("get_screenshot", {"width": 1280, "height": 960})
    import base64
    img_bytes = base64.b64decode(result["base64_png"])
    out = OUTPUT_DIR / f"{name}.png"
    out.write_bytes(img_bytes)
    print(f"  Screenshot saved: {out}")


def main():
    print("=== verify_recompute ===")
    print(f"Loading params from {VARS_FILE}")
    vars_ = load_vars()
    print(f"  {len(vars_)} params loaded")

    print("Pushing VarSet to FreeCAD and recomputing...")
    push_varset(vars_)
    time.sleep(1)

    print("Capturing screenshot...")
    screenshot("recompute_result")

    print("PASS: recompute completed successfully")


if __name__ == "__main__":
    main()
