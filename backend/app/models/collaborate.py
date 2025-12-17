"""Collaboration engine models for persistence and analytics."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class CollaborateRun(Base):
    """Main collaboration run record."""
    
    __tablename__ = "collaborate_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_message_id = Column(String, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    assistant_message_id = Column(String, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    mode = Column(String(16), nullable=False, index=True)  # 'auto' | 'manual'
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String(16), nullable=False, default="running", index=True)  # running | success | error
    error_reason = Column(Text, nullable=True)

    # Quality metrics (NEW)
    query_complexity = Column(Integer, nullable=True)  # 1-5 complexity level
    substance_score = Column(Float, nullable=True)  # 0-10
    completeness_score = Column(Float, nullable=True)  # 0-10
    depth_score = Column(Float, nullable=True)  # 0-10
    accuracy_score = Column(Float, nullable=True)  # 0-10
    overall_quality_score = Column(Float, nullable=True)  # 0-10
    quality_gate_passed = Column(Boolean, nullable=True)
    quality_validation_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    thread = relationship("Thread", foreign_keys=[thread_id])
    user_message = relationship("Message", foreign_keys=[user_message_id])
    assistant_message = relationship("Message", foreign_keys=[assistant_message_id])
    stages = relationship("CollaborateStage", back_populates="run", cascade="all, delete-orphan")
    reviews = relationship("CollaborateReview", back_populates="run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CollaborateRun {self.id} ({self.mode})>"


class CollaborateStage(Base):
    """Individual stage in collaboration pipeline."""
    
    __tablename__ = "collaborate_stages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("collaborate_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_id = Column(String(32), nullable=False)  # 'analyst' | 'researcher' | etc.
    label = Column(String(128), nullable=False)
    provider = Column(String(64), nullable=True)
    model = Column(String(128), nullable=True)
    status = Column(String(16), nullable=False, index=True)  # pending | running | success | error
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    meta = Column(JSONB, nullable=True)  # Additional stage metadata
    
    # Relationships
    run = relationship("CollaborateRun", back_populates="stages")
    
    def __repr__(self):
        return f"<CollaborateStage {self.stage_id} ({self.status})>"


class CollaborateReview(Base):
    """External review from multi-model council."""
    
    __tablename__ = "collaborate_reviews"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("collaborate_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(32), nullable=False)  # 'perplexity' | 'gemini' | 'gpt' | etc.
    provider = Column(String(64), nullable=True)
    model = Column(String(128), nullable=True)
    stance = Column(String(16), nullable=True)  # agree | disagree | mixed | unknown
    content = Column(Text, nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    run = relationship("CollaborateRun", back_populates="reviews")
    
    def __repr__(self):
        return f"<CollaborateReview {self.source} ({self.stance})>"