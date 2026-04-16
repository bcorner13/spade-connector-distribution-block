# QD_Bar — Parametric Spade Connector Distribution Block

Fully parametric 6-slot spade connector distribution bar for a Daytona Coupe gauge harness.
Two bars are printed — one **power**, one **ground**.

**Power bar slot assignment:**
| Slot | Connection |
|------|-----------|
| 1 | Harness power feed |
| 2 | Tach |
| 3 | Gauge white 1 |
| 4 | Gauge white 2 |
| 5 | Gauge white 3 |
| 6 | Gauge white 4 |

The ground bar mirrors the same 6-slot layout.

---

## Files

| File | Description |
|------|-------------|
| `files/QD_Bar.FCStd` | Assembly + VarSet (all params live here) |
| `Distribution Block.FCStd` | Parametric bar body |
| `Lid.FCStd` | Slide-in rail cover with clip tab |
| `cad/Mount.FCStd` | L-bracket standoff for gauge mounting |
| `cad/varsets/qd_bar_vars.json` | Canonical parameter values |

---

## Parametric Usage

1. Open `files/QD_Bar.FCStd` in FreeCAD 1.1+
2. Edit `VarSet` — change **NumSlots**, **SlotSpacing**, etc.
3. FreeCAD recomputes automatically — slots repopulate via LinearPattern

Key parameters:
- `NumSlots` — number of connector slots (default: 6)
- `SlotSpacing` — center-to-center spacing in mm (default: 9.5)
- `SlotWidth` — slot opening width in mm (default: 6.6 for 6.3mm spade + 0.3 clearance)
- `BodyHeight` — overall bar height (default: 22mm)
- `Width` — bar depth (default: 30mm)
- `MountSpan` — gauge stud center-to-center for bracket (default: 120mm)

All derived lengths (bar `Length`, etc.) update automatically from these values.

---

## Print Settings

| Setting | Value |
|---------|-------|
| Material | PLA or PETG |
| Layer height | 0.2 mm |
| Nozzle | 0.4 mm |
| Walls/perimeters | 2 |
| Infill | 20% |
| Orientation | Long axis horizontal; rails printed vertically |

### Tolerances
- `ClearanceSide` (default 0.1mm) — lid rail side play; increase if rails bind
- `ClipClearance` (default 0.05mm) — clip tab engagement gap; increase for looser snap

Adjust per filament shrinkage. PETG typically needs +0.05–0.1mm additional clearance.

### Recommended chamfers/fillets (apply in slicer or model)
- 0.3mm chamfer on groove/rail entry mouth
- 0.5mm fillet on inner slot corners

---

## Mount Bracket

The `Mount.FCStd` L-bracket mounts to the outer M4/5-32" studs on a pair of gauges.
- Stud slots: 5mm wide × 10mm long (fits M4, allows fine alignment)
- Stud span: 120mm center-to-center (set `MountSpan` in VarSet to adjust)
- Riser height: 25mm (clears wiring with 5mm margin over 20mm wire stack)
- Inward shelf: bar drops into retention slots on the shelf top face

---

## Running Tests Locally

Requires FreeCAD 1.1+ with the **FreeCAD MCP Server** addon installed and running (TCP port 9876).

**Prerequisites:**
1. FreeCAD 1.1 installed
2. [FreeCAD MCP Server](https://github.com/your-org/freecad-mcp-server) addon installed and enabled inside FreeCAD
3. These documents open in FreeCAD:
   - `files/QD_Bar.FCStd`
   - `Distribution Block.FCStd`
   - `Lid.FCStd`
   - `cad/Mount.FCStd`

The test scripts connect to the FreeCAD MCP Server via TCP (`FREECAD_MCP_HOST` / `FREECAD_MCP_PORT`, default `127.0.0.1:9876`).

```bash
make test           # full MCP verification suite
make export-stl     # export Distribution_Block, Lid, Mount to files/*.stl
make regen-variants # fuzz NumSlots 2–10, save screenshots to mcp-tests/output/
```

---

## CI

The GitHub Actions workflow (`.github/workflows/cad-ci.yml`) runs **static checks** on every push and PR:
- Required files present (`.FCStd`, `Makefile`, `qd_bar_vars.json`)
- `cad/varsets/qd_bar_vars.json` is valid JSON
- All `mcp-tests/*.py` scripts pass syntax check

Full MCP verification (`make test`) requires FreeCAD 1.1 + MCP addon and runs locally.

---

## Credits

Based on [Spade Connector Distribution Block by frankjay](https://www.thingiverse.com/thing:4854104) (Thingiverse).
