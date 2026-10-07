import os
from app.mcp.server import mcp, identity

if __name__ == "__main__":
    identity.set(os.environ.get("MCP_STDIO_PERSONA", "analyst"))
    mcp.run(transport="stdio")
