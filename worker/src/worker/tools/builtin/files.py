import os
from pathlib import Path
from worker.config.settings import settings

WORKSPACE = Path(settings.workspace_dir).resolve()


def list_files(subfolder: str = "") -> str:
    folder = (WORKSPACE / subfolder).resolve()
    if not folder.is_relative_to(WORKSPACE):
        return "Error: access outside the workspace is not allowed."
    if not folder.is_dir():
        return f"Error: '{subfolder}' is not a folder."
    names = [p.name + ("/" if p.is_dir() else "") for p in sorted(folder.iterdir())]
    return "\n".join(names) or "(empty folder)"

def read_file(path: str) -> str:
    file = (WORKSPACE / path).resolve()
    if not file.is_relative_to(WORKSPACE):
        return "Error: access outside the workspace is not allowed."
    if not file.is_file():
        return f"Error: '{path}' is not a file."
    text = file.read_text(encoding="utf-8", errors="replace")
    return text[:4000]  # keep the context small for local models


READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a text file from the user's workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path inside the workspace."}
            },
            "required": ["path"],
        },
    },
}


LIST_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List the files and folders in the user's workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "subfolder": {
                    "type": "string",
                    "description": "Subfolder inside the workspace. Empty string for the root.",
                }
            },
            "required": [],
        },
    },
}

TOOLS = {"list_files": list_files, "read_file": read_file}
SCHEMAS = [LIST_FILES_SCHEMA, READ_FILE_SCHEMA]