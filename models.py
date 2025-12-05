# Antigravity Ultra - Multi-Model Orchestration
import asyncio
import httpx
from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass
import json

from config import config, MODELS


@dataclass
class ChatMessage:
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class ModelResponse:
    content: str
    model: str
    tokens_used: int
    finish_reason: str


class GroqClient:
    """Client for Groq API (FREE & ultra-fast)"""
    
    BASE_URL = "https://api.groq.com/openai/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.groq_api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
    
    async def chat(
        self,
        messages: List[ChatMessage],
        model: str = "llama-3.1-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> ModelResponse:
        """Send a chat completion request"""
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return ModelResponse(
            content=data["choices"][0]["message"]["content"],
            model=data["model"],
            tokens_used=data["usage"]["total_tokens"],
            finish_reason=data["choices"][0]["finish_reason"]
        )
    
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        model: str = "llama-3.1-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion"""
        async with self.client.stream(
            "POST",
            "/chat/completions",
            json={
                "model": model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if chunk["choices"][0]["delta"].get("content"):
                            yield chunk["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue
    
    async def close(self):
        await self.client.aclose()


class OllamaClient:
    """Client for local Ollama models"""
    
    BASE_URL = "http://localhost:11434"
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=120.0
        )
        self._available = None
    
    async def is_available(self) -> bool:
        """Check if Ollama is running"""
        if self._available is not None:
            return self._available
        try:
            response = await self.client.get("/api/tags")
            self._available = response.status_code == 200
        except Exception:
            self._available = False
        return self._available
    
    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        if not await self.is_available():
            return []
        response = await self.client.get("/api/tags")
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    
    async def chat(
        self,
        messages: List[ChatMessage],
        model: str = "llama3.1",
        temperature: float = 0.7
    ) -> ModelResponse:
        """Send a chat request to Ollama"""
        response = await self.client.post(
            "/api/chat",
            json={
                "model": model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
                "options": {"temperature": temperature}
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return ModelResponse(
            content=data["message"]["content"],
            model=model,
            tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            finish_reason="stop"
        )
    
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        model: str = "llama3.1",
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from Ollama"""
        async with self.client.stream(
            "POST",
            "/api/chat",
            json={
                "model": model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": True,
                "options": {"temperature": temperature}
            }
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("message", {}).get("content"):
                            yield data["message"]["content"]
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    
    async def close(self):
        await self.client.aclose()


class ModelOrchestrator:
    """Orchestrates multiple LLM providers with fallback"""
    
    def __init__(self):
        self.groq = GroqClient()
        self.ollama = OllamaClient()
        self._ollama_available = None
    
    async def get_available_models(self) -> Dict[str, List[str]]:
        """Get all available models by provider"""
        models = {
            "groq": list(k for k, v in MODELS.items() if v.provider == "groq")
        }
        
        if await self.ollama.is_available():
            models["ollama"] = await self.ollama.list_models()
        
        return models
    
    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> ModelResponse:
        """Send a chat request to the best available model"""
        model = model or config.default_model
        
        # Try Groq first (fastest)
        if model in MODELS and MODELS[model].provider == "groq":
            try:
                return await self.groq.chat(messages, model, temperature, max_tokens)
            except Exception as e:
                print(f"Groq error: {e}, trying fallback...")
        
        # Try Ollama as fallback
        if await self.ollama.is_available():
            ollama_model = model.replace("ollama/", "") if model.startswith("ollama/") else "llama3.1"
            try:
                return await self.ollama.chat(messages, ollama_model, temperature)
            except Exception as e:
                print(f"Ollama error: {e}")
        
        raise RuntimeError("No LLM provider available")
    
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response from the best available model"""
        model = model or config.default_model
        
        # Try Groq first
        if model in MODELS and MODELS[model].provider == "groq":
            try:
                async for chunk in self.groq.chat_stream(messages, model, temperature, max_tokens):
                    yield chunk
                return
            except Exception as e:
                print(f"Groq stream error: {e}, trying fallback...")
        
        # Try Ollama
        if await self.ollama.is_available():
            ollama_model = model.replace("ollama/", "") if model.startswith("ollama/") else "llama3.1"
            async for chunk in self.ollama.chat_stream(messages, ollama_model, temperature):
                yield chunk
            return
        
        raise RuntimeError("No LLM provider available for streaming")
    
    async def close(self):
        await self.groq.close()
        await self.ollama.close()


# Global orchestrator instance
orchestrator = ModelOrchestrator()
