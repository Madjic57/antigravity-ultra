# Antigravity Ultra - FastAPI Server
import sys
import os
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import json
import asyncio

from config import config, MODELS
from models import orchestrator, ChatMessage
from agent import agent
from memory import memory


# === Pydantic Models ===

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None
    use_agent: bool = True


class ConversationCreate(BaseModel):
    title: str = ""


# === FastAPI App ===

app = FastAPI(
    title="Antigravity Ultra",
    description="IA Autonome Ultra-Performante",
    version="1.0.0"
)


# === API Endpoints ===

@app.on_event("startup")
async def startup():
    """Connect to database on startup"""
    await memory.connect()
    print("[API] Database connected")


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Antigravity Ultra",
        "version": "1.0.0",
        "database": config.database_url.split(":")[0]
    }


@app.get("/api/models")
async def list_models():
    """List available models"""
    available = await orchestrator.get_available_models()
    
    models_info = []
    for provider, model_list in available.items():
        for model_name in model_list:
            info = MODELS.get(model_name, {})
            models_info.append({
                "name": model_name,
                "provider": provider,
                "context_length": getattr(info, 'context_length', 8192) if info else 8192,
                "speed": getattr(info, 'speed', 'medium') if info else 'medium'
            })
    
    return {"models": models_info, "default": config.default_model}


@app.post("/api/conversations")
async def create_conversation(data: ConversationCreate):
    """Create a new conversation"""
    conv_id = str(uuid.uuid4())
    await memory.create_conversation(conv_id, data.title)
    return {"conversation_id": conv_id, "title": data.title}


@app.get("/api/conversations")
async def list_conversations():
    """List all conversations"""
    conversations = await memory.list_conversations()
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "updated_at": c.updated_at.isoformat(),
                "message_count": c.message_count
            }
            for c in conversations
        ]
    }


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a conversation with messages"""
    messages = await memory.get_messages(conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat()
            }
            for m in messages
        ]
    }


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    await memory.delete_conversation(conversation_id)
    return {"message": "Conversation deleted"}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with streaming"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            request = json.loads(data)
            
            message = request.get("message", "")
            conv_id = request.get("conversation_id") or str(uuid.uuid4())
            model = request.get("model")
            use_agent = request.get("use_agent", True)
            
            # Save user message
            await memory.add_message(conv_id, "user", message)
            
            # Send conversation ID
            await websocket.send_json({
                "type": "conversation_id",
                "conversation_id": conv_id
            })
            
            if use_agent:
                # Use agent with tools
                full_response = ""
                async for event in agent.chat(message, model):
                    if event["type"] == "chunk":
                        full_response += event["content"]
                        await websocket.send_json({
                            "type": "chunk",
                            "content": event["content"]
                        })
                    elif event["type"] == "tool_call":
                        await websocket.send_json({
                            "type": "tool_call",
                            "name": event["name"],
                            "arguments": event["arguments"]
                        })
                    elif event["type"] == "tool_result":
                        await websocket.send_json({
                            "type": "tool_result",
                            "name": event["name"],
                            "result": event["result"][:500]  # Truncate for display
                        })
                    elif event["type"] == "status":
                        await websocket.send_json({
                            "type": "status",
                            "status": event["status"]
                        })
                
                # Save assistant response
                await memory.add_message(conv_id, "assistant", full_response)
            else:
                # Simple chat without tools
                response = await agent.simple_chat(message, model)
                
                # Send as single chunk
                await websocket.send_json({
                    "type": "chunk",
                    "content": response
                })
                
                # Save response
                await memory.add_message(conv_id, "assistant", response)
            
            # Signal completion
            await websocket.send_json({"type": "done"})
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


# === Static Files ===

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    """Serve the main page"""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Antigravity Ultra API", "docs": "/docs"}


# === Startup/Shutdown ===

@app.on_event("shutdown")
async def shutdown():
    await memory.disconnect()
    await agent.close()
