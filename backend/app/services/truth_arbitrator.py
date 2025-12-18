"""
Truth Arbitration Engine - Ground-Truth Conflict Resolver

Models frequently hallucinate or contradict each other. This creates a Truth 
Arbitration Engine where any disagreement triggers a "truth duel" and each 
model must provide citations or reasoning.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import re
import time
from collections import defaultdict

class ConflictType(Enum):
    """Types of conflicts that can occur between models"""
    FACTUAL = "factual"           # Contradictory facts or data
    METHODOLOGICAL = "methodological"  # Different approaches to same problem
    INTERPRETIVE = "interpretive"      # Different interpretations of same data
    SCOPE = "scope"              # Different scope or context assumptions
    TEMPORAL = "temporal"        # Information from different time periods
    SOURCE = "source"            # Conflicting sources or authorities

@dataclass
class Claim:
    """Individual claim made by a model"""
    text: str
    source_model: str
    confidence: float
    citations: List[str] = field(default_factory=list)
    reasoning: str = ""
    context: str = ""
    timestamp: float = field(default_factory=time.time)

@dataclass
class ConflictResolution:
    """Result of conflict arbitration"""
    conflict_id: str
    conflict_type: ConflictType
    conflicting_claims: List[Claim]
    final_verdict: str
    confidence_score: float
    reasoning: str
    winning_claim: Optional[Claim]
    evidence_summary: Dict[str, Any]
    arbitration_method: str
    resolution_time_ms: float

class TruthArbitrator:
    """Intelligent system for resolving conflicts between model outputs"""
    
    def __init__(self):
        self.conflict_patterns = self._build_conflict_patterns()
        self.authority_weights = self._initialize_authority_weights()
        self.resolution_history = []
    
    def _build_conflict_patterns(self) -> Dict[ConflictType, List[str]]:
        """Build patterns for detecting different types of conflicts"""
        return {
            ConflictType.FACTUAL: [
                r'\b(is|are)\s+(\w+)\s*,?\s*but\s+.*(is|are)\s+(\w+)',
                r'\b(\d+)\b.*but.*\b(\d+)\b',  # Numerical conflicts
                r'\b(true|false)\b.*\b(false|true)\b',
                r'\b(correct|incorrect)\b.*\b(incorrect|correct)\b'
            ],
            ConflictType.METHODOLOGICAL: [
                r'\bshould\s+use\s+(\w+).*instead.*use\s+(\w+)',
                r'\bbest\s+approach\s+is\s+(\w+).*better\s+to\s+(\w+)',
                r'\brecommend\s+(\w+).*prefer\s+(\w+)'
            ],
            ConflictType.INTERPRETIVE: [
                r'\bmeans\s+(\w+).*actually\s+means\s+(\w+)',
                r'\binterpret.*as\s+(\w+).*interpret.*as\s+(\w+)',
                r'\bsignifies\s+(\w+).*indicates\s+(\w+)'
            ],
            ConflictType.TEMPORAL: [
                r'\bin\s+(\d{4}).*in\s+(\d{4})',  # Different years
                r'\bcurrently\s+(\w+).*previously\s+(\w+)',
                r'\bnow\s+(\w+).*then\s+(\w+)'
            ]
        }
    
    def _initialize_authority_weights(self) -> Dict[str, Dict[str, float]]:
        """Initialize domain-specific authority weights for different models"""
        return {
            "research": {
                "sonar-pro": 0.9,       # Perplexity excels at research
                "gemini-2.0-flash": 0.8,
                "gpt-4o": 0.7,
                "claude-3-5-sonnet": 0.7,
                "kimi": 0.6
            },
            "reasoning": {
                "claude-3-5-sonnet": 0.9,  # Claude excels at reasoning
                "gpt-4o": 0.8,
                "kimi": 0.7,
                "gemini-2.0-flash": 0.7,
                "sonar-pro": 0.5
            },
            "code": {
                "gpt-4o": 0.9,          # GPT-4 excels at code
                "claude-3-5-sonnet": 0.8,
                "kimi": 0.7,
                "gemini-2.0-flash": 0.6,
                "sonar-pro": 0.4
            },
            "factual": {
                "sonar-pro": 0.9,       # Perplexity for facts
                "gemini-2.0-flash": 0.8,
                "claude-3-5-sonnet": 0.7,
                "gpt-4o": 0.6,
                "kimi": 0.6
            }
        }

    async def resolve_conflicts(
        self, 
        claims: List[Dict[str, Any]], 
        context: str = ""
    ) -> List[ConflictResolution]:
        """
        Main method to resolve conflicts between multiple claims.
        
        Args:
            claims: List of claim dictionaries with text, source_model, confidence
            context: Additional context for conflict resolution
        
        Returns:
            List of conflict resolutions
        """
        start_time = time.perf_counter()
        
        # Convert to Claim objects
        claim_objects = [
            Claim(
                text=claim['text'],
                source_model=claim['source_model'],
                confidence=claim['confidence'],
                citations=claim.get('citations', []),
                reasoning=claim.get('reasoning', ''),
                context=context
            )
            for claim in claims
        ]
        
        # Detect conflicts
        conflicts = await self._detect_conflicts(claim_objects)
        
        # Resolve each conflict
        resolutions = []
        for i, conflict_claims in enumerate(conflicts):
            resolution = await self._arbitrate_conflict(
                conflict_id=f"conflict_{int(time.time())}_{i}",
                conflicting_claims=conflict_claims,
                context=context
            )
            resolutions.append(resolution)
        
        # Store resolution history
        self.resolution_history.extend(resolutions)
        
        # Limit history size
        if len(self.resolution_history) > 100:
            self.resolution_history = self.resolution_history[-50:]
        
        return resolutions
    
    async def _detect_conflicts(self, claims: List[Claim]) -> List[List[Claim]]:
        """Detect conflicting claims using pattern matching and semantic analysis"""
        
        conflicts = []
        
        # Compare each pair of claims
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                claim1, claim2 = claims[i], claims[j]
                
                # Skip if same model (models don't conflict with themselves)
                if claim1.source_model == claim2.source_model:
                    continue
                
                conflict_detected, conflict_type = self._analyze_claim_conflict(claim1, claim2)
                
                if conflict_detected:
                    # Check if this conflict is already in our list
                    existing_conflict = None
                    for conflict_group in conflicts:
                        if claim1 in conflict_group or claim2 in conflict_group:
                            existing_conflict = conflict_group
                            break
                    
                    if existing_conflict:
                        # Add to existing conflict group
                        if claim1 not in existing_conflict:
                            existing_conflict.append(claim1)
                        if claim2 not in existing_conflict:
                            existing_conflict.append(claim2)
                    else:
                        # Create new conflict group
                        conflicts.append([claim1, claim2])
        
        return conflicts
    
    def _analyze_claim_conflict(self, claim1: Claim, claim2: Claim) -> Tuple[bool, ConflictType]:
        """Analyze if two claims conflict and determine conflict type"""
        
        text1 = claim1.text.lower()
        text2 = claim2.text.lower()
        
        # Check each conflict type pattern
        for conflict_type, patterns in self.conflict_patterns.items():
            for pattern in patterns:
                # Look for contradictory patterns across claims
                if self._texts_contradict(text1, text2, pattern):
                    return True, conflict_type
        
        # Semantic contradiction detection
        if self._semantic_contradiction_check(text1, text2):
            return True, ConflictType.FACTUAL
        
        return False, ConflictType.FACTUAL
    
    def _texts_contradict(self, text1: str, text2: str, pattern: str) -> bool:
        """Check if two texts contradict based on a specific pattern"""
        
        # Simple contradiction patterns
        contradictory_pairs = [
            ("not", "is"), ("cannot", "can"), ("never", "always"),
            ("impossible", "possible"), ("false", "true"), 
            ("incorrect", "correct"), ("no", "yes")
        ]
        
        for negative, positive in contradictory_pairs:
            if negative in text1 and positive in text2:
                # Check if they're talking about the same thing
                # (crude similarity check - enhance with embeddings in production)
                common_words = set(text1.split()) & set(text2.split())
                if len(common_words) >= 2:  # At least 2 words in common
                    return True
            
            if positive in text1 and negative in text2:
                common_words = set(text1.split()) & set(text2.split())
                if len(common_words) >= 2:
                    return True
        
        return False
    
    def _semantic_contradiction_check(self, text1: str, text2: str) -> bool:
        """Basic semantic contradiction detection"""
        
        # Check for numerical contradictions
        numbers1 = re.findall(r'\b\d+\.?\d*\b', text1)
        numbers2 = re.findall(r'\b\d+\.?\d*\b', text2)
        
        if numbers1 and numbers2:
            # If both contain numbers and they're significantly different
            try:
                num1 = float(numbers1[0])
                num2 = float(numbers2[0])
                
                # Check if numbers are talking about similar context
                context_words = set(text1.split()) & set(text2.split())
                if len(context_words) >= 2 and abs(num1 - num2) / max(num1, num2) > 0.5:
                    return True
            except (ValueError, ZeroDivisionError, IndexError) as num_error:
                # Numerical comparison failed, continue with other checks
                pass
            except Exception as e:
                logger.warning(f"Unexpected error in numerical contradiction check: {e}")
                pass
        
        # Check for explicit contradictions
        explicit_contradictions = [
            ("increase", "decrease"), ("rise", "fall"), ("grow", "shrink"),
            ("better", "worse"), ("faster", "slower"), ("higher", "lower")
        ]
        
        for word1, word2 in explicit_contradictions:
            if word1 in text1 and word2 in text2:
                context_words = set(text1.split()) & set(text2.split())
                if len(context_words) >= 2:
                    return True
        
        return False
    
    async def _arbitrate_conflict(
        self, 
        conflict_id: str, 
        conflicting_claims: List[Claim],
        context: str
    ) -> ConflictResolution:
        """Arbitrate a specific conflict using multiple resolution strategies"""
        
        start_time = time.perf_counter()
        
        # Determine conflict type
        conflict_type = self._determine_conflict_type(conflicting_claims)
        
        # Apply multiple arbitration methods
        arbitration_results = []
        
        # Method 1: Citation-based arbitration
        citation_result = self._arbitrate_by_citations(conflicting_claims)
        arbitration_results.append(("citation", citation_result))
        
        # Method 2: Confidence-based arbitration
        confidence_result = self._arbitrate_by_confidence(conflicting_claims)
        arbitration_results.append(("confidence", confidence_result))
        
        # Method 3: Model authority arbitration
        authority_result = self._arbitrate_by_authority(conflicting_claims, conflict_type)
        arbitration_results.append(("authority", authority_result))
        
        # Method 4: Evidence quality arbitration
        evidence_result = self._arbitrate_by_evidence_quality(conflicting_claims)
        arbitration_results.append(("evidence", evidence_result))
        
        # Meta-arbitration: choose best method
        final_result = self._meta_arbitrate(arbitration_results, conflicting_claims)
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        return ConflictResolution(
            conflict_id=conflict_id,
            conflict_type=conflict_type,
            conflicting_claims=conflicting_claims,
            final_verdict=final_result['verdict'],
            confidence_score=final_result['confidence'],
            reasoning=final_result['reasoning'],
            winning_claim=final_result['winning_claim'],
            evidence_summary=final_result['evidence'],
            arbitration_method=final_result['method'],
            resolution_time_ms=execution_time
        )
    
    def _determine_conflict_type(self, claims: List[Claim]) -> ConflictType:
        """Determine the primary type of conflict"""
        
        # Check for factual indicators
        for claim in claims:
            text = claim.text.lower()
            if any(word in text for word in ['fact', 'true', 'false', 'correct', 'incorrect']):
                return ConflictType.FACTUAL
        
        # Check for methodological indicators
        for claim in claims:
            text = claim.text.lower()
            if any(word in text for word in ['should', 'recommend', 'approach', 'method']):
                return ConflictType.METHODOLOGICAL
        
        # Check for interpretive indicators
        for claim in claims:
            text = claim.text.lower()
            if any(word in text for word in ['means', 'interpret', 'signifies', 'indicates']):
                return ConflictType.INTERPRETIVE
        
        return ConflictType.FACTUAL  # Default
    
    def _arbitrate_by_citations(self, claims: List[Claim]) -> Dict[str, Any]:
        """Arbitrate based on quality and quantity of citations"""
        
        scored_claims = []
        
        for claim in claims:
            citation_score = 0.0
            
            # Count citations
            citation_count = len(claim.citations)
            citation_score += min(citation_count * 0.2, 0.6)  # Max 0.6 from count
            
            # Quality of citations (basic URL analysis)
            for citation in claim.citations:
                if 'doi.org' in citation or '.edu' in citation:
                    citation_score += 0.15  # Academic sources
                elif '.gov' in citation:
                    citation_score += 0.1   # Government sources
                elif any(domain in citation for domain in ['wikipedia', 'stackoverflow', 'github']):
                    citation_score += 0.05  # Community sources
            
            scored_claims.append((claim, citation_score))
        
        # Find best claim
        best_claim, best_score = max(scored_claims, key=lambda x: x[1])
        
        return {
            "winning_claim": best_claim,
            "confidence": min(best_score, 0.9),
            "verdict": f"Based on citations analysis: {best_claim.text[:100]}...",
            "reasoning": f"Winner had {len(best_claim.citations)} citations with quality score {best_score:.2f}"
        }
    
    def _arbitrate_by_confidence(self, claims: List[Claim]) -> Dict[str, Any]:
        """Arbitrate based on model confidence scores"""
        
        # Weight confidence by model reliability
        weighted_scores = []
        
        for claim in claims:
            # Base score is the claim confidence
            score = claim.confidence
            
            # Adjust for model reliability (simple heuristic)
            if claim.source_model == "claude-3-5-sonnet":
                score *= 1.1  # Claude bonus for reasoning
            elif claim.source_model == "sonar-pro":
                score *= 1.05  # Perplexity bonus for facts
            
            weighted_scores.append((claim, score))
        
        best_claim, best_score = max(weighted_scores, key=lambda x: x[1])
        
        return {
            "winning_claim": best_claim,
            "confidence": best_score,
            "verdict": f"Highest confidence claim: {best_claim.text[:100]}...",
            "reasoning": f"Winner had confidence score {best_claim.confidence:.2f} from {best_claim.source_model}"
        }
    
    def _arbitrate_by_authority(self, claims: List[Claim], conflict_type: ConflictType) -> Dict[str, Any]:
        """Arbitrate based on model authority in relevant domain"""
        
        # Map conflict type to domain
        domain_map = {
            ConflictType.FACTUAL: "factual",
            ConflictType.METHODOLOGICAL: "reasoning", 
            ConflictType.INTERPRETIVE: "reasoning",
            ConflictType.SCOPE: "reasoning",
            ConflictType.TEMPORAL: "factual",
            ConflictType.SOURCE: "research"
        }
        
        domain = domain_map.get(conflict_type, "factual")
        authority_weights = self.authority_weights.get(domain, {})
        
        scored_claims = []
        
        for claim in claims:
            authority_score = authority_weights.get(claim.source_model, 0.5)
            # Combine with claim confidence
            final_score = authority_score * 0.7 + claim.confidence * 0.3
            scored_claims.append((claim, final_score))
        
        best_claim, best_score = max(scored_claims, key=lambda x: x[1])
        
        return {
            "winning_claim": best_claim,
            "confidence": best_score,
            "verdict": f"Domain authority winner: {best_claim.text[:100]}...",
            "reasoning": f"Winner: {best_claim.source_model} has highest authority in {domain} domain"
        }
    
    def _arbitrate_by_evidence_quality(self, claims: List[Claim]) -> Dict[str, Any]:
        """Arbitrate based on quality of reasoning and evidence"""
        
        scored_claims = []
        
        for claim in claims:
            evidence_score = 0.0
            text = claim.text.lower()
            
            # Length and detail bonus
            if len(claim.text) > 100:
                evidence_score += 0.1
            if len(claim.text) > 300:
                evidence_score += 0.1
            
            # Reasoning indicators
            reasoning_words = ['because', 'since', 'due to', 'as a result', 'therefore', 'thus']
            reasoning_count = sum(1 for word in reasoning_words if word in text)
            evidence_score += min(reasoning_count * 0.1, 0.3)
            
            # Specificity indicators
            if re.search(r'\d+', text):  # Contains numbers
                evidence_score += 0.1
            if any(word in text for word in ['specifically', 'precisely', 'exactly']):
                evidence_score += 0.1
            
            # Uncertainty penalty
            uncertainty_words = ['might', 'could', 'possibly', 'perhaps', 'maybe']
            uncertainty_count = sum(1 for word in uncertainty_words if word in text)
            evidence_score -= uncertainty_count * 0.05
            
            scored_claims.append((claim, evidence_score))
        
        best_claim, best_score = max(scored_claims, key=lambda x: x[1])
        
        return {
            "winning_claim": best_claim,
            "confidence": min(best_score + 0.5, 0.9),  # Base confidence boost
            "verdict": f"Best evidence quality: {best_claim.text[:100]}...",
            "reasoning": f"Winner had highest evidence quality score: {best_score:.2f}"
        }
    
    def _meta_arbitrate(
        self, 
        arbitration_results: List[Tuple[str, Dict[str, Any]]], 
        claims: List[Claim]
    ) -> Dict[str, Any]:
        """Meta-arbitration: choose the best arbitration method result"""
        
        # Count votes for each claim
        claim_votes = defaultdict(list)
        
        for method, result in arbitration_results:
            winning_claim = result.get('winning_claim')
            confidence = result.get('confidence', 0.5)
            
            if winning_claim:
                claim_votes[winning_claim].append((method, confidence))
        
        # Find claim with most votes and highest average confidence
        best_claim = None
        best_score = 0.0
        best_methods = []
        
        for claim, votes in claim_votes.items():
            vote_count = len(votes)
            avg_confidence = sum(confidence for _, confidence in votes) / vote_count
            
            # Score = vote count + average confidence
            score = vote_count + avg_confidence
            
            if score > best_score:
                best_score = score
                best_claim = claim
                best_methods = [method for method, _ in votes]
        
        # Build comprehensive verdict
        if best_claim:
            verdict = f"**RESOLVED:** {best_claim.text}"
            reasoning = f"Consensus from {len(best_methods)} methods: {', '.join(best_methods)}"
            
            # Add confidence meter
            confidence_level = min(best_score / (len(arbitration_results) + 1), 0.95)
            
            if confidence_level > 0.8:
                confidence_indicator = "🟢 HIGH"
            elif confidence_level > 0.6:
                confidence_indicator = "🟡 MEDIUM"
            else:
                confidence_indicator = "🔴 LOW"
            
            verdict += f"\n\n**Confidence:** {confidence_indicator} ({confidence_level:.1%})"
            
        else:
            # Fallback if no consensus
            best_claim = max(claims, key=lambda c: c.confidence)
            verdict = f"**NO CONSENSUS:** Using highest confidence claim: {best_claim.text}"
            reasoning = "No clear winner from arbitration methods, falling back to confidence"
            confidence_level = 0.3
        
        return {
            "winning_claim": best_claim,
            "confidence": confidence_level,
            "verdict": verdict,
            "reasoning": reasoning,
            "method": "meta_arbitration",
            "evidence": {
                "methods_used": [method for method, _ in arbitration_results],
                "consensus_level": len(claim_votes.get(best_claim, [])) / len(arbitration_results),
                "total_claims": len(claims),
                "arbitration_results": arbitration_results
            }
        }
    
    def get_arbitration_stats(self) -> Dict[str, Any]:
        """Get statistics about arbitration performance"""
        
        if not self.resolution_history:
            return {"total_resolutions": 0}
        
        # Calculate stats
        total_resolutions = len(self.resolution_history)
        avg_confidence = sum(r.confidence_score for r in self.resolution_history) / total_resolutions
        avg_resolution_time = sum(r.resolution_time_ms for r in self.resolution_history) / total_resolutions
        
        conflict_type_counts = defaultdict(int)
        method_counts = defaultdict(int)
        
        for resolution in self.resolution_history:
            conflict_type_counts[resolution.conflict_type.value] += 1
            method_counts[resolution.arbitration_method] += 1
        
        return {
            "total_resolutions": total_resolutions,
            "avg_confidence": avg_confidence,
            "avg_resolution_time_ms": avg_resolution_time,
            "conflict_types": dict(conflict_type_counts),
            "arbitration_methods": dict(method_counts),
            "high_confidence_rate": len([r for r in self.resolution_history if r.confidence_score > 0.8]) / total_resolutions
        }