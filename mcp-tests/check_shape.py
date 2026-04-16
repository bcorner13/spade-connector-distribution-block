#!/usr/bin/env python3
"""
check_shape.py
Shape analysis + design rule checks against qd_bar_vars.json.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_client import mcp  # noqa: E402

VARS_FILE = Path(__file__).parent.parent / "cad" / "varsets" / "qd_bar_vars.json"
NOZZLE_DIAMETER = float(os.environ.get("NOZZLE_DIAMETER", "0.4"))
TOL = 0.5  # mm bounding-box tolerance

FAILURES = []


def fail(msg: str):
    FAILURES.append(msg)
    print(f"  FAIL: {msg}")


def ok(msg: str):
    print(f"  ok:   {msg}")


def load_vars():
    with open(VARS_FILE) as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def query_varset_derived() -> dict:
    """Query computed/derived values from the Params VarSet in FreeCAD."""
    script = """
import FreeCAD
vs = FreeCAD.getDocument("Params").getObject("VarSet")
print(f"BlockLength:{float(vs.BlockLength):.4f}")
print(f"BlockWidth:{float(vs.BlockWidth):.4f}")
# Body_Pad height determines actual Z dimension
doc = FreeCAD.getDocument("Distribution_Block")
pad = doc.getObject("Body_Pad")
print(f"PadHeight:{float(pad.Length):.4f}")
# Rail width for DRC
rail_w = float(vs.GrooveW) - max(0.05, float(vs.ClearanceSide))
print(f"Rail_Width:{rail_w:.4f}")
"""
    result = mcp("execute_script", {"script": script})
    stdout = result.get("stdout", "")
    d: dict = {}
    for line in stdout.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            try:
                d[key] = float(val)
            except ValueError:
                pass
    return d


def get_shape_info(doc: str, obj: str) -> dict:
    """Get bounding box and volume via execute_script using the Tip feature shape."""
    script = f"""
import FreeCAD
doc = FreeCAD.getDocument("{doc}")
obj = doc.getObject("{obj}")
if obj is None:
    print("SHAPE_ERROR:object not found")
else:
    shape = obj.Tip.Shape if hasattr(obj, 'Tip') and obj.Tip else obj.Shape
    bb = shape.BoundBox
    print(f"BBOX:{{bb.XLength:.4f}},{{bb.YLength:.4f}},{{bb.ZLength:.4f}}")
    print(f"VOLUME:{{shape.Volume:.4f}}")
"""
    result = mcp("execute_script", {"script": script})
    stdout = result.get("stdout", "")
    info: dict = {}
    for line in stdout.splitlines():
        if line.startswith("SHAPE_ERROR:"):
            raise RuntimeError(line[12:])
        if line.startswith("BBOX:"):
            parts = line[5:].split(",")
            info["x_size"] = float(parts[0])
            info["y_size"] = float(parts[1])
            info["z_size"] = float(parts[2])
        if line.startswith("VOLUME:"):
            info["volume"] = float(line[7:])
    return info


def check_bounding_box(info: dict, exp_x, exp_y, exp_z, label):
    dx = info.get("x_size", 0)
    dy = info.get("y_size", 0)
    dz = info.get("z_size", 0)
    for axis, got, exp in [("X", dx, exp_x), ("Y", dy, exp_y), ("Z", dz, exp_z)]:
        if exp is None:
            continue
        if abs(got - exp) > TOL:
            fail(f"{label} bounding box {axis}: expected {exp:.2f} got {got:.2f} (tol ±{TOL})")
        else:
            ok(f"{label} {axis}={got:.2f} (expected {exp:.2f})")


def check_min_feature(size, name):
    min_feat = NOZZLE_DIAMETER * 1.5
    if size < min_feat:
        fail(f"{name}={size:.2f}mm is below min printable feature ({min_feat:.2f}mm)")
    else:
        ok(f"{name}={size:.2f}mm >= min feature {min_feat:.2f}mm")


def main():
    print("=== check_shape ===")
    v = load_vars()
    d = query_varset_derived()

    # --- Distribution_Block body ---
    print("\n[Distribution_Block: Body]")
    try:
        res = get_shape_info("Distribution_Block", "Body")
        check_bounding_box(res, d["BlockLength"], d["BlockWidth"], d["PadHeight"], "Body")
    except Exception as e:
        fail(f"get_shape_info Body: {e}")

    # --- Slot width DRC ---
    print("\n[Slot width DRC]")
    min_slot = 6.3 + max(0.05, v["ClearanceSide"])
    if v["SlotWidth"] < min_slot:
        fail(f"SlotWidth {v['SlotWidth']} < required {min_slot:.2f}")
    else:
        ok(f"SlotWidth {v['SlotWidth']} >= {min_slot:.2f}")

    # --- Groove printability ---
    print("\n[Groove printability]")
    check_min_feature(v["GrooveW"], "GrooveW")
    check_min_feature(v["GrooveD"], "GrooveD")
    check_min_feature(d["Rail_Width"], "Rail_Width (lid)")

    # --- Wall thickness ---
    print("\n[Wall thickness]")
    if v["WallThick"] < v["MountThick"] * 0.5:
        fail(f"WallThick {v['WallThick']} seems very thin vs MountThick {v['MountThick']}")
    else:
        ok(f"WallThick {v['WallThick']}mm OK")

    # --- Watertight / volume check ---
    print("\n[Watertight checks]")
    for doc, obj in [
        ("Distribution_Block", "Body"),
        ("Lid", "Body"),
        ("Mount", "Body_Bracket"),
    ]:
        try:
            res = get_shape_info(doc, obj)
            vol = res.get("volume", 0)
            if vol <= 0:
                fail(f"{doc}/{obj}: volume={vol} (not watertight?)")
            else:
                ok(f"{doc}/{obj}: volume={vol:.1f} mm³")
        except Exception as e:
            fail(f"{doc}/{obj} shape check failed: {e}")

    # --- Summary ---
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)} issues):")
        for f_ in FAILURES:
            print(f"  - {f_}")
        sys.exit(1)
    else:
        print("PASS: all shape checks passed")


if __name__ == "__main__":
    main()
