"""Router run logging model for dynamic routing analytics."""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class RouterRun(Base):
    """Logs every router decision for analytics and learning."""

    __tablename__ = "router_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # User and session context
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)  # Thread ID or session ID
    thread_id = Column(String, ForeignKey("threads.id", ondelete="SET NULL"), nullable=True, index=True)

    # Intent classification
    task_type = Column(String, nullable=False)  # generic_chat, web_research, etc.
    requires_web = Column(Boolean, nullable=False, default=False)
    requires_tools = Column(Boolean, nullable=False, default=False)
    priority = Column(String, nullable=False)  # quality, speed, cost
    estimated_input_tokens = Column(Integer, nullable=False)

    # Routing decision
    chosen_model_id = Column(String, nullable=False)  # Model ID from ModelConfig
    chosen_provider = Column(String, nullable=False)  # Provider type
    chosen_provider_model = Column(String, nullable=False)  # Actual model name for API

    # Candidate scores (JSON array of {modelId, score})
    scores_json = Column(JSON, nullable=True)

    # Performance metrics
    latency_ms = Column(Integer, nullable=True)  # Actual latency
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)

    # User feedback (updated later)
    user_rating = Column(Integer, nullable=True)  # 1-5 rating
    user_liked = Column(Boolean, nullable=True)  # Thumbs up/down

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    thread = relationship("Thread", foreign_keys=[thread_id])

    def __repr__(self):
        return f"<RouterRun {self.id} ({self.chosen_model_id})>"











