"""
mcp_client.py
Shared TCP client for the FreeCAD MCP Server.

The FreeCAD MCP Server runs a raw TCP JSON-RPC server inside FreeCAD on
port 9876 (newline-delimited messages, not HTTP).  This module provides a
single `mcp()` helper that opens a fresh connection per call, sends the
request, reads the response, and returns the result dict — or raises on
RPC errors.

Environment variables:
  FREECAD_MCP_HOST   RPC server host (default: 127.0.0.1)
  FREECAD_MCP_PORT   RPC server port (default: 9876)
"""

import json
import os
import socket

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
MSG_DELIMITER = b"\n"
TIMEOUT = 120.0  # seconds — generous for slow recomputes

_request_id = 0


def _host() -> str:
    return os.environ.get("FREECAD_MCP_HOST", DEFAULT_HOST)


def _port() -> int:
    return int(os.environ.get("FREECAD_MCP_PORT", str(DEFAULT_PORT)))


def mcp(method: str, params: dict = None) -> object:
    """Send a JSON-RPC request to the FreeCAD MCP Server and return the result."""
    global _request_id
    _request_id += 1

    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": _request_id,
    }
    raw = json.dumps(request).encode() + MSG_DELIMITER

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.connect((_host(), _port()))
        sock.sendall(raw)

        buffer = b""
        while MSG_DELIMITER not in buffer:
            chunk = sock.recv(65536)
            if not chunk:
                raise ConnectionError("Connection closed by FreeCAD MCP Server")
            buffer += chunk
    finally:
        sock.close()

    line, _ = buffer.split(MSG_DELIMITER, 1)
    response = json.loads(line)

    if "error" in response:
        err = response["error"]
        raise RuntimeError(f"RPC error {err.get('code')}: {err.get('message')}")

    return response.get("result")
