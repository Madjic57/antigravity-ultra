# Antigravity Ultra - HuggingFace Free LLM Client
import httpx
from typing import AsyncGenerator, Optional, List
from dataclasses import dataclass
import json


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass 
class ModelResponse:
    content: str
    model: str
    tokens_used: int
    finish_reason: str


class HuggingFaceClient:
    """Client for HuggingFace Inference API (FREE, no API key required)"""
    
    DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.client = httpx.AsyncClient(timeout=120.0, headers=headers)
        self._available = True
        print("[HuggingFace] Free inference client initialized")
    
    def is_available(self) -> bool:
        return self._available
    
    def _format_prompt(self, messages: List[ChatMessage]) -> str:
        """Format messages for Mistral instruction format"""
        prompt = ""
        for msg in messages:
            if msg.role == "system":
                prompt += f"[INST] {msg.content} [/INST]\n"
            elif msg.role == "user":
                prompt += f"[INST] {msg.content} [/INST]\n"
            elif msg.role == "assistant":
                prompt += f"{msg.content}\n"
        return prompt.strip()
    
    async def chat(
        self,
        messages: List[ChatMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> ModelResponse:
        """Send a chat completion request"""
        model = model or self.DEFAULT_MODEL
        url = f"https://api-inference.huggingface.co/models/{model}"
        
        prompt = self._format_prompt(messages)
        
        try:
            response = await self.client.post(
                url,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature,
                        "return_full_text": False,
                        "do_sample": True
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                content = data[0].get("generated_text", "")
            else:
                content = data.get("generated_text", str(data))
            
            return ModelResponse(
                content=content,
                model=model,
                tokens_used=len(content.split()),
                finish_reason="stop"
            )
        except Exception as e:
            print(f"[HuggingFace] Error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream chat response"""
        model = model or self.DEFAULT_MODEL
        url = f"https://api-inference.huggingface.co/models/{model}"
        
        prompt = self._format_prompt(messages)
        
        try:
            response = await self.client.post(
                url,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature,
                        "return_full_text": False,
                        "do_sample": True
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                content = data[0].get("generated_text", "")
            else:
                content = data.get("generated_text", str(data))
            
            # Yield word by word for streaming effect
            words = content.split()
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                
        except Exception as e:
            print(f"[HuggingFace] Stream error: {e}")
            yield f"Erreur HuggingFace: {str(e)}"
    
    async def close(self):
        await self.client.aclose()


# Global instance
huggingface_client = HuggingFaceClient()
