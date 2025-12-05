# Antigravity Ultra - Configuration
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from pathlib import Path


@dataclass
class ModelInfo:
    """Information about an LLM model"""
    name: str
    provider: str
    context_length: int
    speed: str  # "fast", "medium", "slow"
    capabilities: List[str] = field(default_factory=list)


# Available models configuration
MODELS: Dict[str, ModelInfo] = {
    # Groq (FREE & Ultra-fast)
    "llama-3.1-70b-versatile": ModelInfo(
        "llama-3.1-70b-versatile", "groq", 131072, "fast",
        ["chat", "code", "analysis", "reasoning"]
    ),
    "llama-3.1-8b-instant": ModelInfo(
        "llama-3.1-8b-instant", "groq", 131072, "fast",
        ["chat", "quick-tasks"]
    ),
    "mixtral-8x7b-32768": ModelInfo(
        "mixtral-8x7b-32768", "groq", 32768, "fast",
        ["chat", "code", "multilingual"]
    ),
    "gemma2-9b-it": ModelInfo(
        "gemma2-9b-it", "groq", 8192, "fast",
        ["chat", "quick-tasks"]
    ),
    # Ollama (Local)
    "ollama/llama3.1": ModelInfo(
        "llama3.1", "ollama", 128000, "medium",
        ["chat", "code", "offline"]
    ),
    "ollama/mistral": ModelInfo(
        "mistral", "ollama", 32000, "medium",
        ["chat", "code", "offline"]
    ),
}


@dataclass
class Config:
    """Main configuration for Antigravity Ultra"""
    
    # API Keys
    groq_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY")
    )
    
    # Default models
    default_model: str = "llama-3.1-70b-versatile"
    fast_model: str = "llama-3.1-8b-instant"
    code_model: str = "llama-3.1-70b-versatile"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    
    # Agent settings
    max_iterations: int = 10
    enable_code_execution: bool = True
    enable_web_search: bool = True
    enable_file_ops: bool = True
    
    # Memory settings
    memory_enabled: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Paths
    base_dir: Path = field(
        default_factory=lambda: Path(__file__).parent
    )
    
    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"
    
    @property
    def db_path(self) -> Path:
        return self.data_dir / "antigravity.db"
    
    @property
    def chroma_path(self) -> Path:
        return self.data_dir / "chroma"
    
    def __post_init__(self):
        self.data_dir.mkdir(exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load config from environment variables"""
        return cls()


# Global config instance
config = Config.from_env()
