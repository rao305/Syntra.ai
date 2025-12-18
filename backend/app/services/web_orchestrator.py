"""Web Orchestrator: Multi-query search and synthesis for time-sensitive queries.

This module handles:
1. Building multiple search queries
2. Gathering search results (using Perplexity)
3. Deduplicating and sorting by recency
4. Synthesizing a concise, source-grounded answer
"""
from typing import List, Dict, Callable, Awaitable
from datetime import datetime
import asyncio

from app.adapters.perplexity import call_perplexity
from app.models.provider_key import ProviderType

import logging
logger = logging.getLogger(__name__)


def build_queries(user_text: str) -> List[str]:
    """
    Build multiple search queries for comprehensive coverage.
    
    Uses query diversity factor (QDF) hints for Perplexity to get varied results.
    """
    base_query = user_text.strip()
    
    queries = [
        f"{base_query}",
        f"{base_query} --QDF=5",  # Query diversity factor
    ]
    
    # Add site-specific queries for Indian news sources
    indian_sites = [
        "hindustantimes.com",
        "indianexpress.com",
        "timesofindia.indiatimes.com",
        "thehindu.com",
        "ndtv.com"
    ]
    
    for site in indian_sites[:3]:  # Limit to 3 sites to avoid too many queries
        queries.append(f"{base_query} site:{site} --QDF=5")
    
    return queries


def dedupe_keep_recent(items: List[Dict], max_n: int = 12) -> List[Dict]:
    """
    Deduplicate search results, keeping most recent.
    
    Args:
        items: List of result dicts with 'url', 'title', 'snippet', 'date' keys
        max_n: Maximum number of results to return
    
    Returns:
        Deduplicated list sorted by recency (newest first)
    """
    seen = set()
    out = []
    
    for item in items:
        # Use URL as primary key, fallback to title
        key = item.get("url") or item.get("title", "")
        if key and key not in seen:
            out.append(item)
            seen.add(key)
    
    # Sort by date if available (newest first)
    def get_date(item: Dict) -> str:
        date_str = item.get("date", "")
        if not date_str:
            return ""
        return date_str
    
    out.sort(key=get_date, reverse=True)
    
    return out[:max_n]


async def gather_search(
    user_text: str,
    api_key: str,
    model: str = "sonar-pro"
) -> List[Dict]:
    """
    Gather search results from multiple queries.
    
    Uses Perplexity's search capabilities. In production, you might want to:
    - Parallelize queries
    - Use different search providers
    - Add caching
    
    Args:
        user_text: User's query
        api_key: Perplexity API key
        model: Perplexity model to use
    
    Returns:
        List of deduplicated search results
    """
    queries = build_queries(user_text)
    
    # For now, use the first query with Perplexity
    # In production, you could parallelize multiple queries
    # Perplexity already does multi-search internally, so we use it directly
    
    messages = [
        {
            "role": "user",
            "content": queries[0]  # Use base query, Perplexity handles multi-search
        }
    ]
    
    try:
        from app.adapters.perplexity import call_perplexity
        response = await call_perplexity(
            messages=messages,
            model=model,
            api_key=api_key,
            max_tokens=1000  # Allow longer responses for search results
        )
        
        # Extract citations if available
        citations = response.citations or []
        
        # Build result list from citations
        results = []
        if citations:
            for i, citation in enumerate(citations):
                if isinstance(citation, dict):
                    results.append({
                        "title": citation.get("title", ""),
                        "url": citation.get("url", ""),
                        "snippet": citation.get("snippet", ""),
                        "date": citation.get("date", "")
                    })
                elif isinstance(citation, str):
                    # Simple URL string
                    results.append({
                        "title": f"Source {i+1}",
                        "url": citation,
                        "snippet": "",
                        "date": ""
                    })
        else:
            # If no citations, try to extract from raw response
            raw_data = response.raw or {}
            # Perplexity might return citations in different formats
            if "citations" in raw_data:
                citations_data = raw_data["citations"]
                if isinstance(citations_data, list):
                    for i, cit in enumerate(citations_data):
                        if isinstance(cit, str):
                            results.append({
                                "title": f"Source {i+1}",
                                "url": cit,
                                "snippet": "",
                                "date": ""
                            })
        
        return dedupe_keep_recent(results)
    
    except Exception as e:
        logger.info("Search gathering failed: {e}")
        return []


async def synthesize(
    user_text: str,
    docs: List[Dict],
    llm_call: Callable[[str, float, int], Awaitable[str]],
    temperature: float = 0.2,
    max_tokens: int = 400
) -> str:
    """
    Synthesize a concise, source-grounded answer from search results.
    
    Args:
        user_text: Original user query
        docs: List of search result dicts
        llm_call: Async function (prompt, temperature, max_tokens) -> text
        temperature: LLM temperature
        max_tokens: Max tokens for synthesis
    
    Returns:
        Synthesized answer text
    """
    if not docs:
        return "I couldn't find fresh coverage. Want me to broaden the search window?"
    
    # Build compact source list
    bullets = "\n".join(
        f"- {d.get('title', '(no title)')} — {d.get('snippet', '').strip()[:150]} "
        f"(source: {d.get('url', '')})"
        for d in docs[:10]
    )
    
    prompt = (
        "You are DAC. Summarize verified events relevant to the user's query using ONLY the sources below. "
        "Be concise, neutral, and recent (last 48–72 hours). If uncertain, say so briefly.\n\n"
        f"USER QUERY:\n{user_text}\n\n"
        f"SOURCES:\n{bullets}\n\n"
        "Return:\n- 3–6 bullet summary with dates\n- 1-line situational caveat if coverage is limited"
    )
    
    try:
        text = await llm_call(prompt, temperature, max_tokens)
        return text.strip()
    except Exception as e:
        logger.info("Synthesis failed: {e}")
        return "I found some sources but couldn't synthesize them. Want me to try again?"


async def web_multisearch_answer(
    user_text: str,
    api_key: str,
    llm_call: Callable[[str, float, int], Awaitable[str]],
    perplexity_model: str = "sonar-pro"
) -> Dict:
    """
    Complete web multi-search pipeline: gather → synthesize.
    
    Args:
        user_text: User's time-sensitive query
        api_key: API key for search (Perplexity)
        llm_call: Async function for synthesis LLM call
        perplexity_model: Perplexity model for search
    
    Returns:
        Dict with 'text' and 'citations' keys
    """
    docs = await gather_search(user_text, api_key, perplexity_model)
    
    if not docs:
        return {
            "text": "I couldn't find fresh coverage. Want me to broaden the search window?",
            "citations": []
        }
    
    text = await synthesize(user_text, docs, llm_call)
    
    # Extract citation URLs
    citations = [d.get("url") for d in docs[:6] if d.get("url")]
    
    return {
        "text": text,
        "citations": citations
    }

