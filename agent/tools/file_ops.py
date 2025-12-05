# Antigravity Ultra - Agent Tools: File Operations
import os
import shutil
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class FileInfo:
    path: str
    name: str
    is_dir: bool
    size: int
    extension: str


class FileOpsTool:
    """Safe file operations tool"""
    
    def __init__(self, allowed_paths: Optional[List[str]] = None):
        # By default, allow user's home and specific directories
        self.allowed_paths = allowed_paths or [
            str(Path.home()),
            str(Path.home() / "Documents"),
            str(Path.home() / "Desktop"),
            str(Path.home() / ".gemini")
        ]
    
    def _is_path_allowed(self, path: str) -> bool:
        """Check if path is in allowed directories"""
        abs_path = os.path.abspath(path)
        return any(abs_path.startswith(allowed) for allowed in self.allowed_paths)
    
    def read_file(self, path: str) -> str:
        """Read a file's contents"""
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access denied: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_file(self, path: str, content: str) -> str:
        """Write content to a file"""
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access denied: {path}")
        
        # Create parent directories if needed
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"File written: {path}"
    
    def list_directory(self, path: str) -> List[FileInfo]:
        """List contents of a directory"""
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access denied: {path}")
        
        results = []
        for item in Path(path).iterdir():
            stat = item.stat()
            results.append(FileInfo(
                path=str(item),
                name=item.name,
                is_dir=item.is_dir(),
                size=stat.st_size if item.is_file() else 0,
                extension=item.suffix if item.is_file() else ""
            ))
        
        return sorted(results, key=lambda x: (not x.is_dir, x.name.lower()))
    
    def create_directory(self, path: str) -> str:
        """Create a directory"""
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access denied: {path}")
        
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"Directory created: {path}"
    
    def delete_file(self, path: str) -> str:
        """Delete a file (moves to recycle bin conceptually)"""
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access denied: {path}")
        
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        
        return f"Deleted: {path}"
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists"""
        return os.path.exists(path)
    
    def get_file_info(self, path: str) -> FileInfo:
        """Get information about a file"""
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access denied: {path}")
        
        p = Path(path)
        stat = p.stat()
        
        return FileInfo(
            path=str(p),
            name=p.name,
            is_dir=p.is_dir(),
            size=stat.st_size,
            extension=p.suffix
        )


# Tool definitions for the agent
FILE_READ_TOOL = {
    "name": "read_file",
    "description": "Read the contents of a file",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read"
            }
        },
        "required": ["path"]
    }
}

FILE_WRITE_TOOL = {
    "name": "write_file",
    "description": "Write content to a file. Creates the file if it doesn't exist.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path where to write the file"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["path", "content"]
    }
}

LIST_DIR_TOOL = {
    "name": "list_directory",
    "description": "List the contents of a directory",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the directory to list"
            }
        },
        "required": ["path"]
    }
}
