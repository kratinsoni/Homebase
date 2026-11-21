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

def write_file(path: str, content: str) -> str:
    file = (WORKSPACE / path).resolve()
    if not file.is_relative_to(WORKSPACE):
        return "Error: access outside the workspace is not allowed."
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")
    return f"Saved {len(content)} characters to {path}."