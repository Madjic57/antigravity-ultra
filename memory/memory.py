# Antigravity Ultra - Memory System
import databases
import sqlalchemy
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config


@dataclass
class ConversationMessage:
    id: Optional[int]
    conversation_id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None


@dataclass
class Conversation:
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


# === Database Schema ===
metadata = sqlalchemy.MetaData()

conversations = sqlalchemy.Table(
    "conversations",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("title", sqlalchemy.String, default=""),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, default=datetime.utcnow),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, default=datetime.utcnow),
)

messages = sqlalchemy.Table(
    "messages",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("conversation_id", sqlalchemy.String, sqlalchemy.ForeignKey("conversations.id"), nullable=False),
    sqlalchemy.Column("role", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("content", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime, default=datetime.utcnow),
    sqlalchemy.Column("metadata", sqlalchemy.Text, default="{}"),
)


class MemoryManager:
    """Persistent memory storage (Async - SQLite/PostgreSQL)"""
    
    def __init__(self):
        self.database_url = config.database_url
        self.database = databases.Database(self.database_url)
        print(f"[Memory] Initialized with {self.database_url.split(':')[0]} database")
    
    async def connect(self):
        """Connect to the database and create tables"""
        await self.database.connect()
        
        # Create tables (only works for SQLite/Postgres with proper permissions)
        # using sync SQLAlchemy engine for schema creation
        engine = sqlalchemy.create_engine(self.database_url)
        metadata.create_all(engine)
        
    async def disconnect(self):
        """Disconnect from the database"""
        await self.database.disconnect()
    
    async def create_conversation(self, conv_id: str, title: str = "") -> str:
        """Create a new conversation"""
        query = conversations.insert().values(
            id=conv_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        try:
            await self.database.execute(query)
            return conv_id
        except Exception as e:
            # Ignore if exists (could be race condition or re-run)
            print(f"[Memory] Create conversation error (ignored): {e}")
            return conv_id
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a message to a conversation"""
        # Ensure conversation exists
        await self.create_conversation(conversation_id)
        
        # Insert message
        query = messages.insert().values(
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=json.dumps(metadata or {})
        )
        message_id = await self.database.execute(query)
        
        # Update conversation timestamp
        update_query = conversations.update().where(
            conversations.c.id == conversation_id
        ).values(updated_at=datetime.utcnow())
        await self.database.execute(update_query)
        
        return message_id
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get messages from a conversation"""
        query = messages.select().where(
            messages.c.conversation_id == conversation_id
        ).order_by(messages.c.timestamp.asc())
        
        if limit:
            query = query.limit(limit)
            
        rows = await self.database.fetch_all(query)
        
        return [
            ConversationMessage(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )
            for row in rows
        ]
    
    async def list_conversations(self, limit: int = 50) -> List[Conversation]:
        """List all conversations"""
        # Simple list without join to be safer across DBs initially
        query = conversations.select().order_by(
            conversations.c.updated_at.desc()
        ).limit(limit)
        
        rows = await self.database.fetch_all(query)
        
        result = []
        for row in rows:
            # Get message count separately
            count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(messages).where(
                messages.c.conversation_id == row["id"]
            )
            count = await self.database.fetch_val(count_query)
            
            result.append(Conversation(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                message_count=count or 0
            ))
        return result
    
    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation"""
        # Delete messages first
        await self.database.execute(
            messages.delete().where(messages.c.conversation_id == conversation_id)
        )
        # Delete conversation
        await self.database.execute(
            conversations.delete().where(conversations.c.id == conversation_id)
        )
    
    async def search_messages(self, query_text: str, limit: int = 20) -> List[ConversationMessage]:
        """Search messages by content"""
        # Use simple LIKE query
        query = messages.select().where(
            messages.c.content.ilike(f"%{query_text}%")
        ).order_by(messages.c.timestamp.desc()).limit(limit)
        
        rows = await self.database.fetch_all(query)
        
        return [
            ConversationMessage(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )
            for row in rows
        ]


# Global memory instance
memory = MemoryManager()

