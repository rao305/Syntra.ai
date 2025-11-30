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


# ---------- Visualization & Image specs ----------

VisualizationKind = Literal["chart", "table"]
ChartType = Literal["line", "bar", "stacked_bar", "pie", "area", "scatter"]
ImagePurpose = Literal["logo", "diagram", "illustration", "thumbnail", "concept_art"]
AspectRatio = Literal["1:1", "16:9", "4:3", "3:2"]


class DataSeries(BaseModel):
    """A single data series for a chart."""
    name: str
    values: List[float]  # Must match length of labels


class ChartData(BaseModel):
    """Structured data for a chart."""
    labels: List[str]  # X-axis labels (e.g., years, categories)
    series: List[DataSeries]  # One or more data series


class VisualizationSpec(BaseModel):
    """Specification for a chart or table to be rendered."""
    id: str
    kind: VisualizationKind
    title: Optional[str] = None
    description: Optional[str] = None
    chart_type: Optional[ChartType] = None
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    data: Optional[ChartData] = None


class ImageSpec(BaseModel):
    """Specification for an image to be generated."""
    id: str
    purpose: ImagePurpose
    prompt: str  # Detailed text prompt for image generation
    style: Optional[str] = None
    aspect_ratio: Optional[AspectRatio] = "1:1"


class CollabState(BaseModel):
    user_query: str
    analysis: Optional[AnalysisState] = None
    research_notes: Optional[ResearchNotes] = None
    draft: Optional[DraftState] = None
    critique: Optional[CritiqueState] = None
    internal_report: Optional[InternalReport] = None
    visualizations: List[VisualizationSpec] = []
    images: List[ImageSpec] = []


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


# ---------- Rendered visuals ----------

class RenderedChart(BaseModel):
    """A rendered chart (PNG/SVG image)."""
    id: str
    url: str  # S3 or CDN URL
    title: Optional[str] = None
    alt: Optional[str] = None
    mime_type: str = "image/png"  # image/png, image/svg+xml


class GeneratedImage(BaseModel):
    """A generated image from an image model."""
    id: str
    url: str  # S3 or CDN URL
    purpose: ImagePurpose
    alt: Optional[str] = None
    mime_type: str = "image/png"


class Visuals(BaseModel):
    """Collection of rendered charts and generated images."""
    charts: List[RenderedChart] = []
    images: List[GeneratedImage] = []
    generated_at: Optional[datetime] = None


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
    visuals: Optional[Visuals] = None
    meta: CollaborateRunMeta
