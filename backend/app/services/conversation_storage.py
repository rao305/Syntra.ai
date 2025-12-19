"""
Conversation Storage Service

Manages persistent storage of agent outputs and conversation context
for cross-turn references and follow-up questions.

Integrates with the database to store:
- Agent outputs from collaboration turns
- Turn metadata and tagging
- Cross-turn relationship tracking
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, select, func
from sqlalchemy.orm import relationship

from app.database import Base
from app.services.collaboration_engine import AgentOutput, AgentRole


class ConversationTurn(Base):
    """A conversation turn containing multiple agent outputs"""
    __tablename__ = 'conversation_turns'

    id = Column(Integer, primary_key=True)
    turn_id = Column(String(255), unique=True, index=True)
    thread_id = Column(String(255), index=True)
    user_query = Column(Text)
    collaboration_mode = Column(String(50))
    final_report = Column(Text)
    total_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to agent outputs
    agent_outputs = relationship("StoredAgentOutput", back_populates="turn")


class StoredAgentOutput(Base):
    """Individual agent output within a conversation turn"""
    __tablename__ = 'agent_outputs'

    id = Column(Integer, primary_key=True)
    turn_id = Column(String(255), ForeignKey('conversation_turns.turn_id'))
    agent_role = Column(String(50))  # agent_analyst, agent_researcher, etc.
    provider = Column(String(50))    # openai, gemini, perplexity
    content = Column(Text)
    timestamp = Column(DateTime)
    execution_order = Column(Integer)  # 1-5 for the 5 agents

    # Relationship back to turn
    turn = relationship("ConversationTurn", back_populates="agent_outputs")


class ConversationStorageService:
    """Service for storing and retrieving conversation data"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def store_collaboration_turn(
        self,
        turn_id: str,
        thread_id: str,
        user_query: str,
        final_report: str,
        agent_outputs: List[AgentOutput],
        total_time_ms: float,
        collaboration_mode: str = "full"
    ):
        """
        Store a complete collaboration turn with all agent outputs.

        Args:
            turn_id: Unique identifier for this turn
            thread_id: Chat thread this turn belongs to
            user_query: Original user question
            final_report: Synthesizer's final integrated response
            agent_outputs: List of all agent outputs from this turn
            total_time_ms: Total collaboration time
            collaboration_mode: "full", "direct", etc.
        """
        # Create conversation turn record
        turn_record = ConversationTurn(
            turn_id=turn_id,
            thread_id=thread_id,
            user_query=user_query,
            collaboration_mode=collaboration_mode,
            final_report=final_report,
            total_time_ms=int(total_time_ms),
            created_at=datetime.utcnow()
        )

        self.db.add(turn_record)

        # Store each agent output
        for i, output in enumerate(agent_outputs):
            output_record = StoredAgentOutput(
                turn_id=turn_id,
                agent_role=output.role.value,
                provider=output.provider,
                content=output.content,
                timestamp=datetime.fromtimestamp(output.timestamp),
                execution_order=i + 1
            )
            self.db.add(output_record)

        await self.db.commit()

    async def get_turn_by_id(self, turn_id: str) -> Optional[ConversationTurn]:
        """Get a conversation turn by its ID"""
        stmt = select(ConversationTurn).where(ConversationTurn.turn_id == turn_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_agent_output(
        self,
        turn_id: str,
        agent_role: AgentRole
    ) -> Optional[StoredAgentOutput]:
        """Get specific agent output from a turn"""
        stmt = select(StoredAgentOutput).where(
            StoredAgentOutput.turn_id == turn_id,
            StoredAgentOutput.agent_role == agent_role.value
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_outputs_for_turn(self, turn_id: str) -> List[StoredAgentOutput]:
        """Get all agent outputs for a specific turn"""
        stmt = select(StoredAgentOutput).where(
            StoredAgentOutput.turn_id == turn_id
        ).order_by(StoredAgentOutput.execution_order)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_recent_outputs_for_thread(
        self,
        thread_id: str,
        limit: int = 10
    ) -> List[StoredAgentOutput]:
        """Get recent agent outputs for a thread"""
        stmt = select(StoredAgentOutput).join(ConversationTurn).where(
            ConversationTurn.thread_id == thread_id
        ).order_by(StoredAgentOutput.timestamp.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_thread_history(self, thread_id: str) -> List[ConversationTurn]:
        """Get all conversation turns for a thread"""
        stmt = select(ConversationTurn).where(
            ConversationTurn.thread_id == thread_id
        ).order_by(ConversationTurn.created_at)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def search_agent_outputs(
        self,
        agent_role: Optional[AgentRole] = None,
        provider: Optional[str] = None,
        content_search: Optional[str] = None,
        limit: int = 20
    ) -> List[StoredAgentOutput]:
        """
        Search agent outputs with filters.

        Args:
            agent_role: Filter by specific agent role
            provider: Filter by provider (openai, gemini, etc.)
            content_search: Search within content (basic text search)
            limit: Max results to return

        Returns:
            List of matching agent outputs
        """
        stmt = select(StoredAgentOutput)

        if agent_role:
            stmt = stmt.where(StoredAgentOutput.agent_role == agent_role.value)

        if provider:
            stmt = stmt.where(StoredAgentOutput.provider == provider)

        if content_search:
            stmt = stmt.where(StoredAgentOutput.content.contains(content_search))

        stmt = stmt.order_by(StoredAgentOutput.timestamp.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_collaboration_stats(self, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about collaborations.

        Args:
            thread_id: Optional thread to scope stats to

        Returns:
            Dict with collaboration statistics
        """
        query = select(ConversationTurn)

        if thread_id:
            query = query.where(ConversationTurn.thread_id == thread_id)

        result = await self.db.execute(query)
        turns = result.scalars().all()

        if not turns:
            return {"total_turns": 0}

        total_turns = len(turns)
        avg_time = sum(turn.total_time_ms for turn in turns) / total_turns

        # Count by collaboration mode
        mode_counts = {}
        for turn in turns:
            mode = turn.collaboration_mode
            mode_counts[mode] = mode_counts.get(mode, 0) + 1

        # Count agent outputs by role
        outputs_query = select(StoredAgentOutput)
        if thread_id:
            outputs_query = outputs_query.join(ConversationTurn).where(
                ConversationTurn.thread_id == thread_id
            )

        outputs_result = await self.db.execute(outputs_query)
        outputs = outputs_result.scalars().all()
        role_counts = {}
        for output in outputs:
            role = output.agent_role
            role_counts[role] = role_counts.get(role, 0) + 1

        return {
            "total_turns": total_turns,
            "avg_time_ms": avg_time,
            "mode_distribution": mode_counts,
            "agent_role_distribution": role_counts,
            "total_agent_outputs": len(outputs)
        }


class ConversationContextManager:
    """
    Manages conversation context for the main assistant.

    Provides helper methods for building context from stored conversations
    and formatting agent outputs for use in follow-up questions.
    """

    def __init__(self, storage_service: ConversationStorageService):
        self.storage = storage_service

    async def build_meta_context(
        self,
        thread_id: str,
        limit: int = 5
    ) -> str:
        """
        Build context string for meta-questions about collaboration.

        Args:
            thread_id: Thread to get context from
            limit: Number of recent outputs to include

        Returns:
            Formatted context string with recent agent outputs
        """
        outputs = await self.storage.get_recent_outputs_for_thread(thread_id, limit)

        if not outputs:
            return "No collaboration history found for this thread."

        context_parts = ["Recent collaboration outputs:\n"]

        for output in outputs:
            context_parts.append(f"\n{output.agent_role.upper()} ({output.provider}):")
            # Truncate long content for context
            content = output.content[:500] + "..." if len(output.content) > 500 else output.content
            context_parts.append(content)

        return "\n".join(context_parts)

    async def get_latest_final_report(self, thread_id: str) -> Optional[str]:
        """Get the most recent final report (synthesizer output) for a thread"""
        outputs = await self.storage.get_recent_outputs_for_thread(thread_id, limit=10)

        for output in outputs:
            if output.agent_role == AgentRole.SYNTHESIZER.value:
                return output.content

        return None

    async def build_followup_context(
        self,
        thread_id: str,
        user_question: str
    ) -> Optional[str]:
        """
        Build context for follow-up questions that reference previous output.

        Args:
            thread_id: Thread to get context from
            user_question: User's follow-up question

        Returns:
            Formatted context string with relevant previous output
        """
        final_report = await self.get_latest_final_report(thread_id)

        if not final_report:
            return None

        return f"""Previous final report:
{final_report}

User follow-up question: {user_question}

Please provide a detailed response that builds on the existing final report. Maintain the same quality and structure while addressing the specific follow-up question."""

    def format_agent_outputs_for_messages(
        self,
        agent_outputs: List[StoredAgentOutput]
    ) -> List[Dict[str, str]]:
        """
        Format stored agent outputs as messages for chat history.

        Args:
            agent_outputs: List of stored agent outputs

        Returns:
            List of message dicts compatible with chat systems
        """
        messages = []

        for output in agent_outputs:
            messages.append({
                "role": output.agent_role,
                "name": output.provider,
                "content": output.content,
                "timestamp": output.timestamp.isoformat(),
                "turn_id": output.turn_id
            })

        return messages