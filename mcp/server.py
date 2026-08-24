#!/usr/bin/env python3
import sys
import json
import logging
from typing import Dict, Any
from backend.app.core.database import SessionLocal
from mcp.tools import MCPToolRegistry

# Configure stderr logging so stdin/stdout remain clean for JSON-RPC JSON lines
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s - %(levelname)s - %(message)s")

def send_response(response: Dict[str, Any]):
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()

def main():
    """
    Standard Model Context Protocol (MCP) Server for Wisualyst Platform.
    Exposes 9 supply chain intelligence tools over JSON-RPC stdio.
    """
    logging.info("Starting Wisualyst MCP Server...")
    db = SessionLocal()
    registry = MCPToolRegistry(db)

    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            # 1. MCP Initialization Handshake
            if method == "initialize":
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "wisualyst-supplychain-mcp",
                            "version": "1.0.0"
                        }
                    }
                })

            elif method == "notifications/initialized":
                # No response needed for initialized notification
                pass

            # 2. List Available Tools
            elif method == "tools/list":
                tools_def = registry.get_tool_definitions()
                mcp_tools = []
                for t in tools_def:
                    mcp_tools.append({
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t["parameters"]
                    })
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": mcp_tools
                    }
                })

            # 3. Execute Tool
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                try:
                    res = registry.execute_tool(tool_name, arguments)
                    send_response({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(res, indent=2, default=str)
                                }
                            ]
                        }
                    })
                except Exception as err:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32603,
                            "message": f"Tool execution failed: {str(err)}"
                        }
                    })

            # Ping
            elif method == "ping":
                send_response({"jsonrpc": "2.0", "id": msg_id, "result": {}})

            else:
                if msg_id:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method '{method}' not found"
                        }
                    })
    finally:
        db.close()

if __name__ == "__main__":
    main()
