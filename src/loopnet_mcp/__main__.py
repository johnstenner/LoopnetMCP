"""Allow running with: python -m loopnet_mcp"""

from loopnet_mcp.server import mcp

mcp.run(transport="stdio")
