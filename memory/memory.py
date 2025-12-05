# Antigravity Ultra - Memory System
import sqlite3
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


class MemoryManager:
    """Persistent memory storage for conversations"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id)
        """)
        
        conn.commit()
        conn.close()
    
    def create_conversation(self, conv_id: str, title: str = "") -> str:
        """Create a new conversation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR IGNORE INTO conversations (id, title) VALUES (?, ?)",
            (conv_id, title)
        )
        
        conn.commit()
        conn.close()
        return conv_id
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a message to a conversation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Ensure conversation exists
        cursor.execute(
            "INSERT OR IGNORE INTO conversations (id) VALUES (?)",
            (conversation_id,)
        )
        
        # Insert message
        cursor.execute(
            """INSERT INTO messages (conversation_id, role, content, metadata)
               VALUES (?, ?, ?, ?)""",
            (conversation_id, role, content, json.dumps(metadata or {}))
        )
        
        # Update conversation timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return message_id
    
    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get messages from a conversation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        query = """
            SELECT id, conversation_id, role, content, timestamp, metadata
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (conversation_id,))
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append(ConversationMessage(
                id=row[0],
                conversation_id=row[1],
                role=row[2],
                content=row[3],
                timestamp=datetime.fromisoformat(row[4]),
                metadata=json.loads(row[5]) if row[5] else {}
            ))
        
        return messages
    
    def get_recent_messages(
        self,
        conversation_id: str,
        count: int = 10
    ) -> List[ConversationMessage]:
        """Get the most recent messages from a conversation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, conversation_id, role, content, timestamp, metadata
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (conversation_id, count))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in reversed(rows):  # Reverse to get chronological order
            messages.append(ConversationMessage(
                id=row[0],
                conversation_id=row[1],
                role=row[2],
                content=row[3],
                timestamp=datetime.fromisoformat(row[4]),
                metadata=json.loads(row[5]) if row[5] else {}
            ))
        
        return messages
    
    def list_conversations(self, limit: int = 50) -> List[Conversation]:
        """List all conversations"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Conversation(
                id=row[0],
                title=row[1] or "",
                created_at=datetime.fromisoformat(row[2]),
                updated_at=datetime.fromisoformat(row[3]),
                message_count=row[4]
            )
            for row in rows
        ]
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all its messages"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        conn.commit()
        conn.close()
    
    def search_messages(self, query: str, limit: int = 20) -> List[ConversationMessage]:
        """Search messages by content"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, conversation_id, role, content, timestamp, metadata
            FROM messages
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f"%{query}%", limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            ConversationMessage(
                id=row[0],
                conversation_id=row[1],
                role=row[2],
                content=row[3],
                timestamp=datetime.fromisoformat(row[4]),
                metadata=json.loads(row[5]) if row[5] else {}
            )
            for row in rows
        ]


# Global memory instance
memory = MemoryManager()
