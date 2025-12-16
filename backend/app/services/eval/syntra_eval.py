"""
SyntraEval - Golden Prompt Nightly Evaluator

Automated evaluator for multi-LLM collaboration system.
Evaluates golden prompts and generates shareable reports for engineering improvements.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class GateResult(str, Enum):
    """Result of a quality gate check."""
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    N_A = "N/A"  # Not applicable (e.g., lexicon lock not provided)


@dataclass
class GoldenTest:
    """A golden test case."""
    test_id: str
    title: str
    user_prompt: str
    expected_output_contract: Dict[str, Any]  # required_headings, file_count, json_schema, etc.
    lexicon_lock: Optional[Dict[str, List[str]]] = None  # allowed_terms, forbidden_terms
    domain_checklist: Optional[List[str]] = None  # Required elements for completeness
    priority: str = "P2"  # P0/P1/P2


@dataclass
class TestRunTranscript:
    """Transcript from a system run."""
    run_id: str
    timestamp: str
    thread_id: Optional[str] = None
    routing: Optional[Dict[str, str]] = None  # provider/model per stage
    repair_attempts: int = 0
    fallback_used: bool = False
    final_output: str = ""
    user_rating: Optional[int] = None  # 1-5
    human_notes: Optional[str] = None


@dataclass
class GateEvaluation:
    """Result of evaluating a single gate."""
    gate_name: str
    result: GateResult
    evidence: Optional[str] = None
    score: int = 0  # Score for this gate (0-100)


@dataclass
class TestEvaluation:
    """Complete evaluation of a single test."""
    test_id: str
    title: str
    gate_a_contract: GateEvaluation
    gate_b_lexicon: GateEvaluation
    gate_c_safety: GateEvaluation
    gate_d_domain: GateEvaluation
    gate_e_quality: GateEvaluation  # Scored, not pass/fail
    gate_score: int  # 0-70
    quality_score: int  # 0-30
    total_score: int  # 0-100
    repair_attempts: int
    fallback_used: bool
    user_rating: Optional[int] = None
    missing_fields: List[str] = None  # If NOT_EVALUABLE


class SyntraEval:
    """Golden Prompt Nightly Evaluator."""

    def __init__(self):
        self.evaluations: List[TestEvaluation] = []

    def evaluate_test(
        self,
        test: GoldenTest,
        transcript: TestRunTranscript
    ) -> TestEvaluation:
        """
        Evaluate a single test case against all gates.
        
        Returns:
            TestEvaluation with all gate results and scores
        """
        # Check if required fields are present
        missing_fields = []
        if not transcript.final_output:
            missing_fields.append("final_output")
        if not test.expected_output_contract:
            missing_fields.append("expected_output_contract")
        
        if missing_fields:
            # Mark as NOT_EVALUABLE
            not_eval = GateResult.NOT_EVALUABLE
            return TestEvaluation(
                test_id=test.test_id,
                title=test.title,
                gate_a_contract=GateEvaluation("Contract", not_eval, f"Missing: {', '.join(missing_fields)}"),
                gate_b_lexicon=GateEvaluation("Lexicon", not_eval),
                gate_c_safety=GateEvaluation("Safety", not_eval),
                gate_d_domain=GateEvaluation("Domain", not_eval),
                gate_e_quality=GateEvaluation("Quality", not_eval),
                gate_score=0,
                quality_score=0,
                total_score=0,
                repair_attempts=transcript.repair_attempts,
                fallback_used=transcript.fallback_used,
                user_rating=transcript.user_rating,
                missing_fields=missing_fields
            )
        
        # Evaluate each gate
        gate_a = self._evaluate_gate_a_contract(
            transcript.final_output,
            test.expected_output_contract
        )
        
        gate_b = self._evaluate_gate_b_lexicon(
            transcript.final_output,
            test.lexicon_lock
        )
        
        gate_c = self._evaluate_gate_c_safety(transcript.final_output)
        
        gate_d = self._evaluate_gate_d_domain(
            transcript.final_output,
            test.domain_checklist
        )
        
        gate_e = self._evaluate_gate_e_quality(transcript.final_output)
        
        # Calculate scores
        gate_score = self._calculate_gate_score(gate_a, gate_b, gate_c, gate_d)
        quality_score = gate_e.score
        
        total_score = gate_score + quality_score
        
        # Apply caps
        if gate_a.result == GateResult.FAIL:
            total_score = min(total_score, 49)
        if gate_c.result == GateResult.FAIL:
            total_score = min(total_score, 39)
        
        return TestEvaluation(
            test_id=test.test_id,
            title=test.title,
            gate_a_contract=gate_a,
            gate_b_lexicon=gate_b,
            gate_c_safety=gate_c,
            gate_d_domain=gate_d,
            gate_e_quality=gate_e,
            gate_score=gate_score,
            quality_score=quality_score,
            total_score=total_score,
            repair_attempts=transcript.repair_attempts,
            fallback_used=transcript.fallback_used,
            user_rating=transcript.user_rating
        )

    def _evaluate_gate_a_contract(
        self,
        output: str,
        contract: Dict[str, Any]
    ) -> GateEvaluation:
        """
        Gate A: Output Contract (highest priority)
        - All required headings/sections exist
        - If "exactly N files" requested, output must include exactly N file blocks
        - If JSON schema expected, output must be valid JSON and match required keys
        """
        if not contract:
            return GateEvaluation("Contract", GateResult.NOT_EVALUABLE, "No contract provided")
        
        violations = []
        evidence_parts = []
        
        # Check required headings
        required_headings = contract.get("required_headings", [])
        if required_headings:
            output_lower = output.lower()
            for heading in required_headings:
                # Check for heading in various formats
                heading_patterns = [
                    rf'#+\s*{re.escape(heading.lower())}',
                    rf'^\s*{re.escape(heading.lower())}\s*$',
                ]
                found = any(re.search(pattern, output_lower, re.MULTILINE) for pattern in heading_patterns)
                if not found:
                    violations.append(f"Missing required heading: '{heading}'")
                    evidence_parts.append(f"'{heading}' not found")
        
        # Check file count
        file_count = contract.get("file_count")
        if file_count is not None:
            # Count code blocks
            code_block_pattern = r'```(?:\w+)?\s*(?:#.*)?\n'
            code_blocks = len(re.findall(code_block_pattern, output))
            
            # Count file headers
            file_header_pattern = r'###\s+`([^`]+)`'
            file_headers = len(re.findall(file_header_pattern, output))
            
            actual_count = max(code_blocks, file_headers)
            
            if actual_count != file_count:
                violations.append(f"File count mismatch: expected {file_count}, found {actual_count}")
                evidence_parts.append(f"Expected {file_count} files, found {actual_count}")
        
        # Check JSON schema
        json_schema = contract.get("json_schema")
        if json_schema:
            try:
                # Try to extract JSON from output
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', output, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    required_keys = json_schema.get("required", [])
                    missing_keys = [key for key in required_keys if key not in parsed]
                    if missing_keys:
                        violations.append(f"Missing JSON keys: {', '.join(missing_keys)}")
                        evidence_parts.append(f"Missing keys: {', '.join(missing_keys)}")
                else:
                    violations.append("No valid JSON found in output")
                    evidence_parts.append("No JSON structure found")
            except json.JSONDecodeError:
                violations.append("Invalid JSON format")
                evidence_parts.append("JSON parsing failed")
        
        if violations:
            return GateEvaluation(
                "Contract",
                GateResult.FAIL,
                "; ".join(evidence_parts),
                score=0
            )
        
        # Score: 30 if pass
        return GateEvaluation("Contract", GateResult.PASS, None, score=30)

    def _evaluate_gate_b_lexicon(
        self,
        output: str,
        lexicon_lock: Optional[Dict[str, List[str]]]
    ) -> GateEvaluation:
        """
        Gate B: Lexicon Lock
        - Forbidden terms must not appear
        - If allowed_terms provided, answer must not introduce terms outside it
        """
        if not lexicon_lock:
            return GateEvaluation("Lexicon", GateResult.N_A)
        
        violations = []
        evidence_parts = []
        
        forbidden_terms = lexicon_lock.get("forbidden_terms", [])
        allowed_terms = lexicon_lock.get("allowed_terms", [])
        
        # Check forbidden terms
        if forbidden_terms:
            output_lower = output.lower()
            for term in forbidden_terms:
                pattern = r'\b' + re.escape(term.lower()) + r'\b'
                matches = re.findall(pattern, output_lower)
                if matches:
                    violations.append(f"Forbidden term '{term}' found")
                    # Quote excerpt
                    match_pos = output_lower.find(term.lower())
                    excerpt_start = max(0, match_pos - 50)
                    excerpt_end = min(len(output), match_pos + len(term) + 50)
                    excerpt = output[excerpt_start:excerpt_end].strip()
                    evidence_parts.append(f"'{term}' in: ...{excerpt}...")
        
        # Check allowed terms (soft check - only flag if introducing new terms for locked concepts)
        # This is a simplified check - full implementation would need semantic understanding
        if allowed_terms and violations:
            # If forbidden terms found, we already failed
            pass
        
        if violations:
            return GateEvaluation(
                "Lexicon",
                GateResult.FAIL,
                "; ".join(evidence_parts),
                score=0
            )
        
        # Score: 20 if pass
        return GateEvaluation("Lexicon", GateResult.PASS, None, score=20)

    def _evaluate_gate_c_safety(self, output: str) -> GateEvaluation:
        """
        Gate C: Safety/Policy
        - No secrets, API keys, or sensitive system content
        """
        violations = []
        evidence_parts = []
        
        # Check for API keys (common patterns)
        api_key_patterns = [
            r'sk-[a-zA-Z0-9]{32,}',  # OpenAI
            r'AIza[0-9A-Za-z_-]{35}',  # Google
            r'[a-zA-Z0-9]{32,}',  # Generic long token
        ]
        
        for pattern in api_key_patterns:
            matches = re.findall(pattern, output)
            if matches:
                violations.append("Potential API key found")
                evidence_parts.append(f"Pattern match: {pattern[:20]}...")
        
        # Check for common secrets
        secret_patterns = [
            r'password\s*[:=]\s*["\']?[^"\'\s]{8,}',
            r'secret\s*[:=]\s*["\']?[^"\'\s]{8,}',
            r'api[_-]?key\s*[:=]\s*["\']?[^"\'\s]{8,}',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                violations.append("Potential secret found")
                evidence_parts.append("Secret pattern detected")
        
        # Check for sensitive system info
        sensitive_patterns = [
            r'/etc/passwd',
            r'/root/',
            r'localhost:\d+',
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                violations.append("Sensitive system path found")
                evidence_parts.append(f"Path pattern: {pattern}")
        
        if violations:
            return GateEvaluation(
                "Safety",
                GateResult.FAIL,
                "; ".join(evidence_parts),
                score=0
            )
        
        # Score: 5 if pass
        return GateEvaluation("Safety", GateResult.PASS, None, score=5)

    def _evaluate_gate_d_domain(
        self,
        output: str,
        domain_checklist: Optional[List[str]]
    ) -> GateEvaluation:
        """
        Gate D: Domain Completeness
        - Check presence of required elements from domain_checklist
        """
        if not domain_checklist:
            return GateEvaluation("Domain", GateResult.N_A)
        
        output_lower = output.lower()
        missing_elements = []
        
        for element in domain_checklist:
            # Check if element appears (flexible matching)
            element_lower = element.lower()
            # Try exact match first
            if element_lower not in output_lower:
                # Try keyword matching
                keywords = element_lower.split()
                if not any(keyword in output_lower for keyword in keywords if len(keyword) > 3):
                    missing_elements.append(element)
        
        if missing_elements:
            return GateEvaluation(
                "Domain",
                GateResult.FAIL,
                f"Missing elements: {', '.join(missing_elements)}",
                score=0
            )
        
        # Score: 15 if pass
        return GateEvaluation("Domain", GateResult.PASS, None, score=15)

    def _evaluate_gate_e_quality(self, output: str) -> GateEvaluation:
        """
        Gate E: Clarity & Actionability (scored, not pass/fail)
        - Is output actionable, concrete, unambiguous?
        - Deduct for vagueness, missing steps, contradictions, repeated content
        """
        score = 30  # Start with full score
        deductions = []
        
        # Check for clarity (headings, structure)
        heading_count = len(re.findall(r'^#+\s+', output, re.MULTILINE))
        if heading_count < 2:
            score -= 3
            deductions.append("Lacks clear structure")
        
        # Check for actionability (concrete steps)
        action_patterns = [
            r'\d+\.\s+',  # Numbered list
            r'[-*]\s+',   # Bullet list
            r'(?:step|action|do|run|execute|create|build|implement)',
        ]
        has_actions = any(re.search(pattern, output.lower()) for pattern in action_patterns)
        if not has_actions:
            score -= 5
            deductions.append("Lacks concrete steps")
        
        # Check for specificity (avoid vague terms)
        vague_terms = ['maybe', 'perhaps', 'might', 'could', 'possibly', 'somewhat', 'kind of']
        vague_count = sum(1 for term in vague_terms if term in output.lower())
        if vague_count > 3:
            score -= min(3, vague_count - 3)
            deductions.append(f"Too many vague terms ({vague_count})")
        
        # Check for contradictions (simple heuristic: check for "but" + negation patterns)
        contradiction_patterns = [
            r'\b(?:but|however|although)\s+.*\b(?:not|no|never|cannot)\b',
        ]
        contradictions = sum(1 for pattern in contradiction_patterns if re.search(pattern, output.lower()))
        if contradictions > 0:
            score -= min(5, contradictions * 2)
            deductions.append(f"Potential contradictions ({contradictions})")
        
        # Check for repeated content (same heading or paragraph appears twice)
        paragraphs = output.split('\n\n')
        seen_paragraphs = set()
        duplicates = 0
        for para in paragraphs:
            para_normalized = para.strip().lower()[:100]  # First 100 chars
            if para_normalized in seen_paragraphs and len(para_normalized) > 20:
                duplicates += 1
            seen_paragraphs.add(para_normalized)
        
        if duplicates > 0:
            score -= min(5, duplicates * 2)
            deductions.append(f"Repeated content ({duplicates} duplicates)")
        
        # Ensure score is in valid range
        score = max(0, min(30, score))
        
        evidence = "; ".join(deductions) if deductions else None
        
        return GateEvaluation("Quality", GateResult.PASS, evidence, score=score)

    def _calculate_gate_score(
        self,
        gate_a: GateEvaluation,
        gate_b: GateEvaluation,
        gate_c: GateEvaluation,
        gate_d: GateEvaluation
    ) -> int:
        """Calculate gate score (0-70)."""
        score = 0
        
        # Contract: 0-30
        if gate_a.result == GateResult.PASS:
            score += gate_a.score
        elif gate_a.result == GateResult.NOT_EVALUABLE:
            # Don't penalize if not evaluable
            pass
        
        # Lexicon: 0-20
        if gate_b.result == GateResult.PASS:
            score += gate_b.score
        elif gate_b.result == GateResult.N_A:
            # Not applicable, don't add or subtract
            pass
        
        # Safety: 0-5
        if gate_c.result == GateResult.PASS:
            score += gate_c.score
        
        # Domain: 0-15
        if gate_d.result == GateResult.PASS:
            score += gate_d.score
        elif gate_d.result == GateResult.N_A:
            # Not applicable
            pass
        
        return score

    def generate_report(
        self,
        evaluations: List[TestEvaluation],
        run_metadata: Dict[str, Any],
        prior_run: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate the nightly evaluation report in Markdown format.
        
        Args:
            evaluations: List of test evaluations
            run_metadata: Metadata about the run (date, build, environment, etc.)
            prior_run: Optional prior run data for trend analysis
        
        Returns:
            Markdown report string
        """
        lines = []
        
        # Header
        lines.append("# Nightly Golden Prompt Evaluation Report")
        lines.append("")
        
        # 1) Run Metadata
        lines.append("## 1) Run Metadata")
        lines.append(f"- Date: {run_metadata.get('date', 'N/A')}")
        lines.append(f"- Build/commit: {run_metadata.get('build_commit', 'N/A')}")
        lines.append(f"- Environment: {run_metadata.get('environment', 'N/A')}")
        lines.append(f"- Providers enabled: {', '.join(run_metadata.get('providers_enabled', []))}")
        lines.append(f"- Total tests: {len(evaluations)}")
        lines.append(f"- Notes: {run_metadata.get('notes', 'None')}")
        lines.append("")
        
        # 2) Executive Summary
        lines.append("## 2) Executive Summary")
        
        # Calculate statistics
        contract_passes = sum(1 for e in evaluations if e.gate_a_contract.result == GateResult.PASS)
        contract_rate = (contract_passes / len(evaluations) * 100) if evaluations else 0
        
        lexicon_tests = [e for e in evaluations if e.gate_b_lexicon.result != GateResult.N_A]
        lexicon_passes = sum(1 for e in lexicon_tests if e.gate_b_lexicon.result == GateResult.PASS)
        lexicon_rate = (lexicon_passes / len(lexicon_tests) * 100) if lexicon_tests else 0
        
        avg_score = sum(e.total_score for e in evaluations) / len(evaluations) if evaluations else 0
        
        repair_rate = sum(1 for e in evaluations if e.repair_attempts > 0) / len(evaluations) * 100 if evaluations else 0
        fallback_rate = sum(1 for e in evaluations if e.fallback_used) / len(evaluations) * 100 if evaluations else 0
        
        # Top regressions (lowest scores)
        sorted_by_score = sorted(evaluations, key=lambda e: e.total_score)
        top_regressions = [e.test_id for e in sorted_by_score[:5]]
        
        lines.append(f"- Pass rate (Contract): {contract_rate:.1f}%")
        lines.append(f"- Pass rate (Lexicon, when applicable): {lexicon_rate:.1f}%")
        lines.append(f"- Average score: {avg_score:.1f}/100")
        lines.append(f"- Repair rate: {repair_rate:.1f}%")
        lines.append(f"- Fallback rate: {fallback_rate:.1f}%")
        lines.append(f"- Top regressions: {', '.join(top_regressions)}")
        lines.append("")
        
        # 3) Results Table
        lines.append("## 3) Results Table (All Tests)")
        lines.append("")
        lines.append("| test_id | title | contract | lexicon | domain | safety | score | repairs | fallback | user_rating |")
        lines.append("|---------|-------|----------|---------|--------|--------|-------|---------|----------|-------------|")
        
        for eval in evaluations:
            lexicon_val = eval.gate_b_lexicon.result.value
            domain_val = eval.gate_d_domain.result.value
            fallback_val = "yes" if eval.fallback_used else "no"
            user_rating_val = str(eval.user_rating) if eval.user_rating else "N/A"
            
            lines.append(
                f"| {eval.test_id} | {eval.title[:30]} | {eval.gate_a_contract.result.value} | "
                f"{lexicon_val} | {domain_val} | {eval.gate_c_safety.result.value} | "
                f"{eval.total_score} | {eval.repair_attempts} | {fallback_val} | {user_rating_val} |"
            )
        
        lines.append("")
        
        # 4) Failures & Evidence
        lines.append("## 4) Failures & Evidence (Grouped)")
        failures = [e for e in evaluations if any(
            g.result == GateResult.FAIL for g in [
                e.gate_a_contract, e.gate_b_lexicon, e.gate_c_safety, e.gate_d_domain
            ]
        )]
        
        if failures:
            for eval in failures:
                lines.append(f"### {eval.test_id}: {eval.title}")
                failed_gates = []
                if eval.gate_a_contract.result == GateResult.FAIL:
                    failed_gates.append("Contract")
                if eval.gate_b_lexicon.result == GateResult.FAIL:
                    failed_gates.append("Lexicon")
                if eval.gate_c_safety.result == GateResult.FAIL:
                    failed_gates.append("Safety")
                if eval.gate_d_domain.result == GateResult.FAIL:
                    failed_gates.append("Domain")
                
                lines.append(f"**Failed gates:** {', '.join(failed_gates)}")
                
                # Add evidence
                for gate in [eval.gate_a_contract, eval.gate_b_lexicon, eval.gate_c_safety, eval.gate_d_domain]:
                    if gate.result == GateResult.FAIL and gate.evidence:
                        lines.append(f"- **{gate.gate_name}:** {gate.evidence}")
                
                lines.append("")
        else:
            lines.append("No gate failures found.")
            lines.append("")
        
        # 5) Trend Notes (if prior run provided)
        if prior_run:
            lines.append("## 5) Trend Notes")
            # Simple comparison - could be enhanced
            prior_avg = prior_run.get('average_score', 0)
            if avg_score > prior_avg:
                lines.append(f"- **Improvements:** Average score increased from {prior_avg:.1f} to {avg_score:.1f}")
            elif avg_score < prior_avg:
                lines.append(f"- **Regressions:** Average score decreased from {prior_avg:.1f} to {avg_score:.1f}")
            else:
                lines.append(f"- **Stable:** Average score remains at {avg_score:.1f}")
            lines.append("")
        
        # 6) Action Plan
        lines.append("## 6) Action Plan (Engineering)")
        
        # Generate action items from failures
        action_items = []
        
        # Analyze failures by type
        contract_failures = [e for e in failures if e.gate_a_contract.result == GateResult.FAIL]
        lexicon_failures = [e for e in failures if e.gate_b_lexicon.result == GateResult.FAIL]
        safety_failures = [e for e in failures if e.gate_c_safety.result == GateResult.FAIL]
        domain_failures = [e for e in failures if e.gate_d_domain.result == GateResult.FAIL]
        
        if contract_failures:
            action_items.append({
                "symptom": f"{len(contract_failures)} tests failed Contract gate",
                "likely_cause": "Output contract validator / prompt instructions",
                "suggested_fix": "Strengthen output contract validation in judge agent prompt",
                "where": "backend/app/services/council/agents/judge.py",
                "metric": "Contract pass rate"
            })
        
        if lexicon_failures:
            action_items.append({
                "symptom": f"{len(lexicon_failures)} tests failed Lexicon gate",
                "likely_cause": "Lexicon lock enforcement / repair logic",
                "suggested_fix": "Add lexicon lock validation to quality gates and repair logic",
                "where": "backend/app/services/council/quality_gates.py",
                "metric": "Lexicon pass rate"
            })
        
        if safety_failures:
            action_items.append({
                "symptom": f"{len(safety_failures)} tests failed Safety gate",
                "likely_cause": "Safety filter / output sanitization",
                "suggested_fix": "Add safety filter to post-processing pipeline",
                "where": "backend/app/services/council/orchestrator.py",
                "metric": "Safety pass rate"
            })
        
        # Low quality scores
        low_quality = [e for e in evaluations if e.quality_score < 20]
        if low_quality:
            action_items.append({
                "symptom": f"{len(low_quality)} tests have low quality scores (<20/30)",
                "likely_cause": "Synthesizer / Judge prompt clarity",
                "suggested_fix": "Enhance clarity and actionability instructions in synthesizer/judge prompts",
                "where": "backend/app/services/council/agents/synthesizer.py, judge.py",
                "metric": "Average quality score"
            })
        
        # High repair/fallback rate
        if repair_rate > 20 or fallback_rate > 10:
            action_items.append({
                "symptom": f"High repair rate ({repair_rate:.1f}%) or fallback rate ({fallback_rate:.1f}%)",
                "likely_cause": "Initial prompt quality / provider routing",
                "suggested_fix": "Review initial prompts and provider selection logic",
                "where": "backend/app/services/council/orchestrator.py, config.py",
                "metric": "Repair/fallback rate"
            })
        
        # Limit to top 5
        for i, item in enumerate(action_items[:5], 1):
            lines.append(f"### {i}. {item['symptom']}")
            lines.append(f"- **Likely cause:** {item['likely_cause']}")
            lines.append(f"- **Suggested fix:** {item['suggested_fix']}")
            lines.append(f"- **Where to implement:** {item['where']}")
            lines.append(f"- **Expected improvement metric:** {item['metric']}")
            lines.append("")
        
        if not action_items:
            lines.append("No critical issues identified. System performing well.")
            lines.append("")
        
        return "\n".join(lines)

