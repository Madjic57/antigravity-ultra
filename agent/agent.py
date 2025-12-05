# Antigravity Ultra - Agent Engine
import json
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ChatMessage, ModelOrchestrator, orchestrator
from config import config
from agent.tools import WebSearchTool, FileOpsTool, CodeExecutor


class AgentStatus(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    RESPONDING = "responding"


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None


@dataclass
class AgentStep:
    thought: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    response: Optional[str] = None


SYSTEM_PROMPT = """Tu es Antigravity Ultra, une IA autonome ultra-performante créée par Antigravity Labs.

Tu as accès aux outils suivants:

1. **web_search(query)**: Recherche sur le web. Utilise pour des informations actuelles.
2. **read_file(path)**: Lire un fichier.
3. **write_file(path, content)**: Écrire dans un fichier.
4. **list_directory(path)**: Lister le contenu d'un dossier.
5. **execute_python(code)**: Exécuter du code Python.
6. **execute_shell(command)**: Exécuter une commande shell.

Pour utiliser un outil, utilise ce format EXACT dans ta réponse:
```tool
{"name": "nom_outil", "arguments": {"arg1": "valeur1"}}
```

Tu peux appeler plusieurs outils dans une même réponse. Après avoir reçu les résultats, continue ton raisonnement.

Caractéristiques:
- Tu es proactif et résous les problèmes de manière autonome
- Tu expliques ton raisonnement clairement
- Tu utilises les outils quand c'est pertinent
- Tu réponds en français par défaut
- Tu es précis, efficace et utile

Réponds à l'utilisateur de manière complète et utile."""


class Agent:
    """Autonomous AI agent with tool calling capabilities"""
    
    def __init__(self):
        self.orchestrator = orchestrator
        self.web_search = WebSearchTool()
        self.file_ops = FileOpsTool()
        self.code_executor = CodeExecutor()
        self.status = AgentStatus.IDLE
        self.conversation: List[ChatMessage] = []
        self.max_iterations = config.max_iterations
    
    def _parse_tool_calls(self, text: str) -> List[ToolCall]:
        """Extract tool calls from response text"""
        tool_calls = []
        
        # Find all tool blocks
        pattern = r'```tool\s*\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match.strip())
                tool_calls.append(ToolCall(
                    name=data.get("name", ""),
                    arguments=data.get("arguments", {})
                ))
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    async def _execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a tool call and return result"""
        name = tool_call.name
        args = tool_call.arguments
        
        try:
            if name == "web_search":
                result = await self.web_search.search_formatted(
                    args.get("query", ""),
                    args.get("num_results", 5)
                )
            elif name == "read_file":
                result = self.file_ops.read_file(args.get("path", ""))
            elif name == "write_file":
                result = self.file_ops.write_file(
                    args.get("path", ""),
                    args.get("content", "")
                )
            elif name == "list_directory":
                files = self.file_ops.list_directory(args.get("path", ""))
                result = "\n".join([
                    f"{'[DIR]' if f.is_dir else '[FILE]'} {f.name}"
                    for f in files
                ])
            elif name == "execute_python":
                exec_result = await self.code_executor.execute_python(
                    args.get("code", "")
                )
                result = f"Output: {exec_result.output}\n"
                if exec_result.error:
                    result += f"Error: {exec_result.error}\n"
                result += f"Return code: {exec_result.return_code}"
            elif name == "execute_shell":
                exec_result = await self.code_executor.execute_shell(
                    args.get("command", "")
                )
                result = f"Output: {exec_result.output}\n"
                if exec_result.error:
                    result += f"Error: {exec_result.error}"
            else:
                result = f"Unknown tool: {name}"
                
        except Exception as e:
            result = f"Error executing {name}: {str(e)}"
        
        tool_call.result = result
        return result
    
    async def chat(
        self,
        message: str,
        model: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message with potential tool calls"""
        
        # Add user message to conversation
        self.conversation.append(ChatMessage(role="user", content=message))
        
        # Build messages with system prompt
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            *self.conversation
        ]
        
        iteration = 0
        full_response = ""
        
        while iteration < self.max_iterations:
            iteration += 1
            self.status = AgentStatus.THINKING
            
            yield {"type": "status", "status": "thinking", "iteration": iteration}
            
            # Get response from model
            current_response = ""
            async for chunk in self.orchestrator.chat_stream(messages, model):
                current_response += chunk
                yield {"type": "chunk", "content": chunk}
            
            full_response += current_response
            
            # Check for tool calls
            tool_calls = self._parse_tool_calls(current_response)
            
            if not tool_calls:
                # No tools to call, we're done
                break
            
            # Execute tools
            self.status = AgentStatus.TOOL_CALLING
            tool_results = []
            
            for tool_call in tool_calls:
                yield {
                    "type": "tool_call",
                    "name": tool_call.name,
                    "arguments": tool_call.arguments
                }
                
                result = await self._execute_tool(tool_call)
                tool_results.append(f"Tool '{tool_call.name}' result:\n{result}")
                
                yield {
                    "type": "tool_result",
                    "name": tool_call.name,
                    "result": result
                }
            
            # Add tool results to conversation
            tool_message = "\n\n".join(tool_results)
            messages.append(ChatMessage(role="assistant", content=current_response))
            messages.append(ChatMessage(role="user", content=f"Résultats des outils:\n\n{tool_message}\n\nContinue ta réponse."))
        
        # Add final response to conversation
        self.conversation.append(ChatMessage(role="assistant", content=full_response))
        self.status = AgentStatus.IDLE
        
        yield {"type": "done", "full_response": full_response}
    
    async def simple_chat(
        self,
        message: str,
        model: Optional[str] = None
    ) -> str:
        """Simple chat without tool calling"""
        self.conversation.append(ChatMessage(role="user", content=message))
        
        messages = [
            ChatMessage(role="system", content="Tu es Antigravity Ultra, une IA utile et précise. Réponds en français."),
            *self.conversation
        ]
        
        response = await self.orchestrator.chat(messages, model)
        self.conversation.append(ChatMessage(role="assistant", content=response.content))
        
        return response.content
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation = []
    
    async def close(self):
        """Cleanup resources"""
        await self.web_search.close()
        await self.orchestrator.close()


# Global agent instance
agent = Agent()
