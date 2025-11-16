"""Database models and setup for SQLite."""
import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base as async_declarative_base

Base = declarative_base()

class Session(Base):
    """Chat session model."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    workspace_path = Column(String)
    active_repo = Column(String, nullable=True)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    """Chat message model."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")
    tool_calls = relationship("ToolCall", back_populates="message", cascade="all, delete-orphan")

class ToolCall(Base):
    """Tool call and execution result."""
    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    claude_tool_id = Column(String, nullable=True)  # Original Claude tool_use ID
    tool_name = Column(String)
    arguments = Column(Text)  # JSON string
    result = Column(Text, nullable=True)
    status = Column(String)  # 'pending', 'approved', 'executed', 'failed'
    timestamp = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="tool_calls")

# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./chatbot.db"

async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        yield session
