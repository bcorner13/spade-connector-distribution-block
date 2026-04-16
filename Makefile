FREECAD_MCP_HOST ?= 127.0.0.1
FREECAD_MCP_PORT ?= 9876
PYTHON           ?= python3

.PHONY: test export-mesh export-stl regen-variants clean

## Run all MCP verification tests (FreeCAD MCP Server must be running on port 9876)
test:
	FREECAD_MCP_HOST=$(FREECAD_MCP_HOST) FREECAD_MCP_PORT=$(FREECAD_MCP_PORT) \
	$(PYTHON) mcp-tests/run_all.py --mcp-port $(FREECAD_MCP_PORT)

## Export all parts to files/*.stl + files/*.3mf and assembly 3MF
export-mesh:
	FREECAD_MCP_HOST=$(FREECAD_MCP_HOST) FREECAD_MCP_PORT=$(FREECAD_MCP_PORT) \
	$(PYTHON) mcp-tests/export_mesh.py

## Alias for backwards compat
export-stl: export-mesh

## Fuzz sweep: NumSlots 2-10, save screenshots to mcp-tests/output/
regen-variants:
	FREECAD_MCP_HOST=$(FREECAD_MCP_HOST) FREECAD_MCP_PORT=$(FREECAD_MCP_PORT) \
	$(PYTHON) -c "\
import sys; sys.path.insert(0,'mcp-tests'); \
import run_all; run_all.set_mcp_port($(FREECAD_MCP_PORT)); \
import json; from pathlib import Path; \
base = run_all.load_vars(); \
[( run_all.push_varset({**base,'NumSlots':n}), \
   run_all.screenshot(f'variant_slots{n}') ) \
 for n in range(2,11)]; \
run_all.push_varset(base); print('Variants done')"

clean:
	rm -rf mcp-tests/output/*.png mcp-tests/output/*.stl mcp-tests/output/*.log
