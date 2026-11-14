from dotenv import load_dotenv

load_dotenv()  # before the import, so WORKSPACE_DIR is set

from mcp.server.mcpserver import MCPServer
from worker.tools.builtin import files

mcp = MCPServer("homebase-files")


@mcp.tool()
def list_files(subfolder: str = "") -> str:
    """List the files and folders in the user's workspace."""
    return files.list_files(subfolder)


@mcp.tool()
def read_file(path: str) -> str:
    """Read a text file from the user's workspace."""
    return files.read_file(path)


if __name__ == "__main__":
    mcp.run()  # stdio transport