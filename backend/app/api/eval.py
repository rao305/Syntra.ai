"""
SyntraEval API Endpoints

Endpoints for running golden prompt evaluations and generating reports.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import set_rls_context
from app.api.deps import require_org_id
from app.services.eval import SyntraEval, GoldenTest, TestRunTranscript, TestEvaluation

router = APIRouter(prefix="/api/eval", tags=["eval"])
logger = logging.getLogger(__name__)


class GoldenTestRequest(BaseModel):
    """A golden test case."""
    test_id: str
    title: str
    user_prompt: str
    expected_output_contract: Dict[str, Any] = Field(..., description="required_headings, file_count, json_schema, etc.")
    lexicon_lock: Optional[Dict[str, List[str]]] = Field(None, description="allowed_terms, forbidden_terms")
    domain_checklist: Optional[List[str]] = Field(None, description="Required elements for completeness")
    priority: str = Field("P2", description="P0/P1/P2")


class TestRunTranscriptRequest(BaseModel):
    """Transcript from a system run."""
    run_id: str
    timestamp: str
    thread_id: Optional[str] = None
    routing: Optional[Dict[str, str]] = None
    repair_attempts: int = 0
    fallback_used: bool = False
    final_output: str = ""
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    human_notes: Optional[str] = None


class EvaluationRequest(BaseModel):
    """Request to evaluate golden tests."""
    tests: List[GoldenTestRequest] = Field(..., description="List of golden test cases (20-50 items)")
    transcripts: List[TestRunTranscriptRequest] = Field(..., description="Run transcripts, one per test")
    run_metadata: Dict[str, Any] = Field(..., description="Date, build_commit, environment, providers_enabled, notes")
    prior_run: Optional[Dict[str, Any]] = Field(None, description="Prior run data for trend analysis")


class EvaluationResponse(BaseModel):
    """Response from evaluation."""
    report: str = Field(..., description="Markdown evaluation report")
    evaluations: List[Dict[str, Any]] = Field(..., description="Individual test evaluation results")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_golden_tests(
    request: EvaluationRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluate golden prompts and generate a nightly evaluation report.
    
    This endpoint:
    1. Takes a list of golden test cases and their run transcripts
    2. Evaluates each test against all quality gates (A-E)
    3. Generates a comprehensive Markdown report
    4. Returns both the report and detailed evaluation results
    """
    try:
        await set_rls_context(db, org_id)
    except Exception as e:
        logger.error(f"Error setting RLS context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RLS context error: {str(e)}"
        )
    
    # Validate inputs
    if len(request.tests) != len(request.transcripts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mismatch: {len(request.tests)} tests but {len(request.transcripts)} transcripts"
        )
    
    if len(request.tests) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one test is required"
        )
    
    # Create evaluator
    evaluator = SyntraEval()
    
    # Convert requests to domain objects
    tests = [
        GoldenTest(
            test_id=t.test_id,
            title=t.title,
            user_prompt=t.user_prompt,
            expected_output_contract=t.expected_output_contract,
            lexicon_lock=t.lexicon_lock,
            domain_checklist=t.domain_checklist,
            priority=t.priority
        )
        for t in request.tests
    ]
    
    transcripts = [
        TestRunTranscript(
            run_id=t.run_id,
            timestamp=t.timestamp,
            thread_id=t.thread_id,
            routing=t.routing,
            repair_attempts=t.repair_attempts,
            fallback_used=t.fallback_used,
            final_output=t.final_output,
            user_rating=t.user_rating,
            human_notes=t.human_notes
        )
        for t in request.transcripts
    ]
    
    # Evaluate each test
    evaluations = []
    for test, transcript in zip(tests, transcripts):
        evaluation = evaluator.evaluate_test(test, transcript)
        evaluations.append(evaluation)
    
    # Generate report
    report = evaluator.generate_report(
        evaluations=evaluations,
        run_metadata=request.run_metadata,
        prior_run=request.prior_run
    )
    
    # Calculate summary
    contract_passes = sum(1 for e in evaluations if e.gate_a_contract.result.value == "PASS")
    avg_score = sum(e.total_score for e in evaluations) / len(evaluations) if evaluations else 0
    repair_rate = sum(1 for e in evaluations if e.repair_attempts > 0) / len(evaluations) * 100 if evaluations else 0
    
    summary = {
        "total_tests": len(evaluations),
        "contract_pass_rate": (contract_passes / len(evaluations) * 100) if evaluations else 0,
        "average_score": avg_score,
        "repair_rate": repair_rate,
        "fallback_rate": sum(1 for e in evaluations if e.fallback_used) / len(evaluations) * 100 if evaluations else 0,
    }
    
    # Convert evaluations to dict for response
    eval_dicts = [
        {
            "test_id": e.test_id,
            "title": e.title,
            "gate_a_contract": {
                "result": e.gate_a_contract.result.value,
                "evidence": e.gate_a_contract.evidence,
                "score": e.gate_a_contract.score
            },
            "gate_b_lexicon": {
                "result": e.gate_b_lexicon.result.value,
                "evidence": e.gate_b_lexicon.evidence,
                "score": e.gate_b_lexicon.score
            },
            "gate_c_safety": {
                "result": e.gate_c_safety.result.value,
                "evidence": e.gate_c_safety.evidence,
                "score": e.gate_c_safety.score
            },
            "gate_d_domain": {
                "result": e.gate_d_domain.result.value,
                "evidence": e.gate_d_domain.evidence,
                "score": e.gate_d_domain.score
            },
            "gate_e_quality": {
                "result": e.gate_e_quality.result.value,
                "evidence": e.gate_e_quality.evidence,
                "score": e.gate_e_quality.score
            },
            "gate_score": e.gate_score,
            "quality_score": e.quality_score,
            "total_score": e.total_score,
            "repair_attempts": e.repair_attempts,
            "fallback_used": e.fallback_used,
            "user_rating": e.user_rating,
        }
        for e in evaluations
    ]
    
    logger.info(
        f"Generated evaluation report for {len(evaluations)} tests",
        extra={"summary": summary}
    )
    
    return EvaluationResponse(
        report=report,
        evaluations=eval_dicts,
        summary=summary
    )


@router.get("/health")
async def eval_health():
    """Health check for evaluation service."""
    return {"status": "healthy", "service": "SyntraEval"}

