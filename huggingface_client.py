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
    
    # List of free models to try in order
    FREE_MODELS = [
        "HuggingFaceH4/zephyr-7b-beta",
        "microsoft/Phi-3-mini-4k-instruct",
        "google/gemma-1.1-7b-it",
        "mistralai/Mistral-7B-Instruct-v0.2"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.current_model_index = 0
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.client = httpx.AsyncClient(timeout=120.0, headers=headers)
        self._available = True
        print("[HuggingFace] Free inference client initialized with fallback models")
    
    def is_available(self) -> bool:
        return self._available
    
    def _format_prompt(self, messages: List[ChatMessage]) -> str:
        """Format messages for instruction-tuned models"""
        prompt = ""
        for msg in messages:
            if msg.role == "system":
                prompt += f"<|system|>\n{msg.content}\n"
            elif msg.role == "user":
                prompt += f"<|user|>\n{msg.content}\n"
            elif msg.role == "assistant":
                prompt += f"<|assistant|>\n{msg.content}\n"
        return prompt + "<|assistant|>\n"
    
    async def chat(
        self,
        messages: List[ChatMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> ModelResponse:
        """Send a chat completion request with fallback"""
        
        # Try models in sequence
        for model_name in self.FREE_MODELS:
            try:
                print(f"[HuggingFace] Trying model: {model_name}")
                url = f"https://api-inference.huggingface.co/models/{model_name}"
                prompt = self._format_prompt(messages)
                
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
                
                # If model is loading (503), wait or skip
                if response.status_code == 503:
                    print(f"[HuggingFace] Model {model_name} loading, trying next...")
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    content = data[0].get("generated_text", "")
                else:
                    content = data.get("generated_text", str(data))
                
                return ModelResponse(
                    content=content,
                    model=model_name,
                    tokens_used=len(content.split()),
                    finish_reason="stop"
                )
                
            except Exception as e:
                print(f"[HuggingFace] Error with {model_name}: {e}")
                continue
                
        raise RuntimeError("All free HuggingFace models failed. Please configure GROQ_API_KEY.")
    
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream chat response with fallback"""
        
        # Use existing chat method to get full response, then simulate stream
        # This is safer for free API which often doesn't support streaming well
        try:
            response = await self.chat(messages, model, temperature, max_tokens)
            content = response.content
            
            # Yield word by word
            words = content.split()
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                
        except Exception as e:
            print(f"[HuggingFace] Stream error: {e}")
            yield f"Erreur (Tous les modèles gratuits ont échoué): {str(e)}"
    
    async def close(self):
        await self.client.aclose()


# Global instance
huggingface_client = HuggingFaceClient()
