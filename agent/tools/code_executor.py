# Antigravity Ultra - Agent Tools: Code Executor
import subprocess
import tempfile
import os
import sys
from typing import Tuple
from dataclasses import dataclass
import asyncio


@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: str
    return_code: int


class CodeExecutor:
    """Safe Python code execution in sandbox"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.python_path = sys.executable
    
    async def execute_python(self, code: str) -> ExecutionResult:
        """Execute Python code safely"""
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Run in subprocess with timeout
            process = await asyncio.create_subprocess_exec(
                self.python_path, temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir()
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                
                return ExecutionResult(
                    success=process.returncode == 0,
                    output=stdout.decode('utf-8', errors='replace'),
                    error=stderr.decode('utf-8', errors='replace'),
                    return_code=process.returncode
                )
                
            except asyncio.TimeoutError:
                process.kill()
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Execution timed out after {self.timeout} seconds",
                    return_code=-1
                )
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
    
    async def execute_shell(self, command: str) -> ExecutionResult:
        """Execute a shell command (Windows)"""
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.expanduser("~")
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                
                return ExecutionResult(
                    success=process.returncode == 0,
                    output=stdout.decode('utf-8', errors='replace'),
                    error=stderr.decode('utf-8', errors='replace'),
                    return_code=process.returncode
                )
                
            except asyncio.TimeoutError:
                process.kill()
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {self.timeout} seconds",
                    return_code=-1
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                return_code=-1
            )


# Tool definition for the agent
PYTHON_EXEC_TOOL = {
    "name": "execute_python",
    "description": "Execute Python code. Use this to run calculations, process data, or test code.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            }
        },
        "required": ["code"]
    }
}

SHELL_EXEC_TOOL = {
    "name": "execute_shell",
    "description": "Execute a shell command. Use with caution.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute"
            }
        },
        "required": ["command"]
    }
}
