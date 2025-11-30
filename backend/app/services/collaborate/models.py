"""Pydantic models for Collaborate pipeline (LLM council architecture)."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ---------- Shared model info ----------

ProviderName = Literal["openai", "google", "perplexity", "kimi", "openrouter"]


class ModelInfo(BaseModel):
    provider: ProviderName
    model_slug: str
    display_name: str


# ---------- Inner collab_state ----------

class AnalysisState(BaseModel):
    intent: str
    normalized_question: str
    subquestions: List[str]
    constraints: List[str]
    target_answer_shape: List[str]
    notes: str


class ResearchNotes(BaseModel):
    facts: List[str] = []
    sources: List[str] = []
    definitions: List[str] = []
    arguments_for: List[str] = []
    arguments_against: List[str] = []
    examples: List[str] = []
    open_questions: List[str] = []


class DraftSection(BaseModel):
    title: str
    body: str


class DraftState(BaseModel):
    content: str
    sections: List[DraftSection] = []


CritiqueSeverity = Literal["low", "medium", "high"]


class CritiqueState(BaseModel):
    issues: List[str] = []
    suggested_improvements: List[str] = []
    severity: CritiqueSeverity
    notes_to_creator: str


ConfidenceLevel = Literal["low", "medium", "high"]


class InternalReport(BaseModel):
    content: str
    high_level_summary: str
    confidence: ConfidenceLevel
    known_gaps: List[str] = []


class CollabState(BaseModel):
    user_query: str
    analysis: Optional[AnalysisState] = None
    research_notes: Optional[ResearchNotes] = None
    draft: Optional[DraftState] = None
    critique: Optional[CritiqueState] = None
    internal_report: Optional[InternalReport] = None


# ---------- Internal pipeline timeline ----------

InternalStageRole = Literal[
    "analyst",
    "researcher",
    "creator",
    "critic",
    "internal_synth",
]


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int


class InternalStage(BaseModel):
    id: str
    role: InternalStageRole
    title: str
    model: ModelInfo
    content: str
    created_at: datetime
    token_usage: Optional[TokenUsage] = None
    latency_ms: Optional[int] = None
    used_in_final_answer: Optional[bool] = None


class CompressedReport(BaseModel):
    model: ModelInfo
    content: str


class InternalPipeline(BaseModel):
    stages: List[InternalStage]
    compressed_report: Optional[CompressedReport] = None


# ---------- External reviews (LLM council) ----------

ExternalReviewerSource = Literal["perplexity", "gemini", "gpt", "kimi", "openrouter"]
ReviewStance = Literal["agree", "disagree", "mixed", "unknown"]


class ExternalReview(BaseModel):
    id: str
    source: ExternalReviewerSource
    model: ModelInfo
    stance: ReviewStance
    content: str
    created_at: datetime
    token_usage: Optional[TokenUsage] = None
    latency_ms: Optional[int] = None


# ---------- Final answer & meta ----------

class FinalAnswerExplanation(BaseModel):
    used_internal_report: bool = True
    external_reviews_considered: int
    confidence_level: ConfidenceLevel


class FinalAnswer(BaseModel):
    content: str
    model: ModelInfo
    created_at: datetime
    explanation: Optional[FinalAnswerExplanation] = None


CollaborateMode = Literal["auto", "manual"]


class CollaborateRunMeta(BaseModel):
    run_id: str
    mode: CollaborateMode
    started_at: datetime
    finished_at: datetime
    total_latency_ms: Optional[int] = None
    models_involved: List[ModelInfo] = []


class CollaborateResponse(BaseModel):
    final_answer: FinalAnswer
    internal_pipeline: InternalPipeline
    external_reviews: List[ExternalReview]
    meta: CollaborateRunMeta
