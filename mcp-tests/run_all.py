#!/usr/bin/env python3
"""
run_all.py
Orchestrates all QD_Bar verification steps. Exits non-zero on any failure.

Usage:
  python3 mcp-tests/run_all.py [--mcp-port 9876]

Environment:
  FREECAD_MCP_HOST  FreeCAD MCP Server host (default: 127.0.0.1)
  FREECAD_MCP_PORT  FreeCAD MCP Server TCP port (default: 9876)
  NOZZLE_DIAMETER   Printer nozzle diameter in mm (default: 0.4)
"""

import argparse
import importlib
import json
import os
import sys
import time
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mcp_client
from mcp_client import mcp

SCRIPT_DIR = Path(__file__).parent
VARS_FILE = SCRIPT_DIR.parent / "cad" / "varsets" / "qd_bar_vars.json"
OUTPUT_DIR = SCRIPT_DIR / "output"
DOC_NAME = "Params"

FUZZ_SLOT_COUNTS = [2, 6, 8]
FUZZ_SLOT_LENGTH_DELTAS = [0.0, -0.5, 0.5]

ALL_FAILURES: list[str] = []


def set_mcp_port(port: int):
    os.environ["FREECAD_MCP_PORT"] = str(port)


def load_vars() -> dict:
    with open(VARS_FILE) as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def push_varset(vars_: dict, doc: str = DOC_NAME):
    assignments = []
    for k, v in vars_.items():
        if isinstance(v, str):
            assignments.append(f'vs.{k} = "{v}"')
        else:
            assignments.append(f"vs.{k} = {v}")
    script = f"""
import FreeCAD
doc = FreeCAD.getDocument("{doc}")
vs = doc.getObject("VarSet")
{chr(10).join(assignments)}
for d in FreeCAD.listDocuments().values():
    d.recompute()
"""
    mcp("execute_script", {"script": script})


def screenshot(name: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = mcp("get_screenshot", {"width": 1280, "height": 960})
    img_bytes = base64.b64decode(result["base64_png"])
    out = OUTPUT_DIR / f"{name}.png"
    out.write_bytes(img_bytes)
    return out


def run_step(label: str, module_path: Path) -> bool:
    """Run a sub-script as a subprocess, capture pass/fail."""
    import subprocess
    print(f"\n{'='*60}")
    print(f"STEP: {label}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, str(module_path)],
        env=os.environ.copy()
    )
    if result.returncode != 0:
        ALL_FAILURES.append(f"{label} returned exit code {result.returncode}")
        return False
    return True


def check_slot_count(num_slots: int) -> bool:
    """Query the LinearPattern feature and assert occurrence count matches."""
    script = """
import FreeCAD
doc = FreeCAD.getDocument("Distribution_Block")
pattern = doc.getObject("Slot_Pattern")
print("SLOT_COUNT:" + str(int(pattern.Occurrences) if pattern else -1))
"""
    try:
        result = mcp("execute_script", {"script": script})
        stdout = result.get("stdout", "")
        got = -1
        for line in stdout.splitlines():
            if line.startswith("SLOT_COUNT:"):
                got = int(line[11:])
        if got != num_slots:
            ALL_FAILURES.append(f"Slot count: expected {num_slots}, got {got}")
            print(f"  FAIL: slot count expected {num_slots} got {got}")
            return False
        print(f"  ok: slot count = {got}")
        return True
    except Exception as e:
        ALL_FAILURES.append(f"Slot count check error: {e}")
        print(f"  FAIL: {e}")
        return False


def fuzz_test():
    """Parametric fuzz: vary NumSlots and SlotSpacing, assert stability."""
    print(f"\n{'='*60}")
    print("STEP: Parametric fuzz test")
    print(f"{'='*60}")
    base = load_vars()
    base_slot_length = base["SlotLength"]
    passed = True

    for ns in FUZZ_SLOT_COUNTS:
        for ds in FUZZ_SLOT_LENGTH_DELTAS:
            slot_len = base_slot_length + ds
            label = f"NumSlots={ns} SlotLength={slot_len}"
            print(f"\n  Fuzz: {label}")
            try:
                fuzz_vars = dict(base)
                fuzz_vars["NumSlots"] = ns
                fuzz_vars["SlotLength"] = slot_len
                push_varset(fuzz_vars)
                time.sleep(0.5)
                sc = screenshot(f"fuzz_slots{ns}_sl{slot_len:.1f}")
                print(f"    Screenshot: {sc.name}")
                # Basic sanity: slot count
                if not check_slot_count(ns):
                    passed = False
            except Exception as e:
                ALL_FAILURES.append(f"Fuzz {label}: {e}")
                print(f"    FAIL: {e}")
                passed = False

    # Restore baseline
    print("\n  Restoring baseline params...")
    push_varset(base)
    return passed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mcp-port", type=int, default=9876)
    args = parser.parse_args()
    set_mcp_port(args.mcp_port)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    steps = [
        ("Verify recompute + screenshot", SCRIPT_DIR / "verify_recompute.py"),
        ("Shape DRC checks",             SCRIPT_DIR / "check_shape.py"),
        ("Sketch diagnostics",           SCRIPT_DIR / "sketch_diagnostics.py"),
        ("Mesh export (STL + 3MF)",      SCRIPT_DIR / "export_mesh.py"),
    ]

    # Slot count check with baseline NumSlots
    print(f"\n{'='*60}")
    print("STEP: Slot count assertion (baseline)")
    print(f"{'='*60}")
    base_vars = load_vars()
    check_slot_count(int(base_vars["NumSlots"]))

    for label, path in steps:
        run_step(label, path)

    # Step 6: fuzz
    fuzz_test()

    print(f"\n{'='*60}")
    if ALL_FAILURES:
        print(f"OVERALL: FAILED ({len(ALL_FAILURES)} issues)")
        for f_ in ALL_FAILURES:
            print(f"  - {f_}")
        sys.exit(1)
    else:
        print("OVERALL: PASS — all verification steps completed successfully")


if __name__ == "__main__":
    main()
