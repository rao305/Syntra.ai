"""
Quality Gates for Syntra Collaboration System

Implements the 5 hard quality gates (A-E) that must pass before final output.
"""

import re
from typing import Dict, List, Optional, Tuple


def check_gate_a_greeting(output: str, user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Gate A: Greeting/Persona Gate
    - Do not greet unless the user greeted in the most recent message.
    
    Returns:
        (passed, violation_message)
    """
    # Check if user greeted
    user_greeted = any(greeting in user_message.lower() for greeting in [
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening'
    ])
    
    # Check if output greets
    output_greeted = any(greeting in output.lower()[:200] for greeting in [
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening'
    ])
    
    if output_greeted and not user_greeted:
        return False, "Output contains greeting but user did not greet"
    
    return True, None


def check_gate_b_lexicon(output: str, lexicon_lock: Optional[Dict[str, List[str]]]) -> Tuple[bool, Optional[str]]:
    """
    Gate B: Lexicon Gate
    - No forbidden terms.
    - Only allowed terms when a lock exists.
    
    Returns:
        (passed, violation_message)
    """
    if not lexicon_lock:
        return True, None
    
    forbidden_terms = lexicon_lock.get('forbidden_terms', [])
    allowed_terms = lexicon_lock.get('allowed_terms', [])
    
    violations = []
    
    # Check for forbidden terms
    if forbidden_terms:
        output_lower = output.lower()
        for term in forbidden_terms:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            if re.search(pattern, output_lower):
                violations.append(f"Forbidden term '{term}' found in output")
    
    # Check for non-allowed terms (if strict lock)
    if allowed_terms and violations:
        # If forbidden terms exist, we already failed
        pass
    elif allowed_terms:
        # Check if output uses terms not in allowed list
        # This is a soft check - we don't enforce strict vocabulary unless explicitly requested
        # For now, we only check if forbidden terms are present
        pass
    
    if violations:
        return False, "; ".join(violations)
    
    return True, None


def check_gate_c_output_contract(output: str, output_contract: Optional[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Gate C: Output Contract Gate
    - Required headings/sections exist exactly as specified.
    - If "exactly N files" requested: output exactly N file blocks.
    
    Returns:
        (passed, violation_message)
    """
    if not output_contract:
        return True, None
    
    violations = []
    
    # Check required headings
    required_headings = output_contract.get('required_headings', [])
    if required_headings:
        output_lower = output.lower()
        for heading in required_headings:
            # Check for heading in various formats (# Heading, ## Heading, etc.)
            heading_patterns = [
                rf'#+\s*{re.escape(heading.lower())}',
                rf'^\s*{re.escape(heading.lower())}\s*$',  # Standalone heading
            ]
            found = any(re.search(pattern, output_lower, re.MULTILINE) for pattern in heading_patterns)
            if not found:
                violations.append(f"Required heading '{heading}' not found")
    
    # Check file count
    file_count = output_contract.get('file_count')
    if file_count is not None:
        # Count code blocks (```filename or ```language)
        code_block_pattern = r'```(?:\w+)?\s*(?:#.*)?\n'
        code_blocks = len(re.findall(code_block_pattern, output))
        
        # Also count file headers like "### `filename`"
        file_header_pattern = r'###\s+`([^`]+)`'
        file_headers = len(re.findall(file_header_pattern, output))
        
        # Use the higher count (some formats use headers, some use code blocks)
        actual_count = max(code_blocks, file_headers)
        
        if actual_count != file_count:
            violations.append(
                f"File count mismatch: expected exactly {file_count} files, found {actual_count}"
            )
    
    # Check format constraints
    format_constraint = output_contract.get('format')
    if format_constraint:
        # Basic format checks
        if format_constraint.lower() == 'markdown' and not output.strip().startswith('#'):
            violations.append("Output should be in markdown format but doesn't start with heading")
    
    if violations:
        return False, "; ".join(violations)
    
    return True, None


def check_gate_d_completeness(output: str) -> Tuple[bool, Optional[str]]:
    """
    Gate D: Completeness Gate (Domain-Agnostic)
    Final output must contain:
    - a clear structure (headings)
    - concrete steps/actions
    - explicit assumptions (if any)
    - risks + mitigations when relevant
    - no duplicated sections
    
    Returns:
        (passed, violation_message)
    """
    violations = []
    
    # Check for clear structure (headings)
    heading_count = len(re.findall(r'^#+\s+', output, re.MULTILINE))
    if heading_count < 2:
        violations.append("Output lacks clear structure (fewer than 2 headings)")
    
    # Check for concrete steps/actions (look for numbered lists or action verbs)
    action_patterns = [
        r'\d+\.\s+',  # Numbered list
        r'[-*]\s+',   # Bullet list
        r'(?:step|action|do|run|execute|create|build|implement)',
    ]
    has_actions = any(re.search(pattern, output.lower()) for pattern in action_patterns)
    if not has_actions:
        violations.append("Output lacks concrete steps/actions")
    
    # Check for duplicated sections (simple heuristic: same heading appears twice)
    headings = re.findall(r'^#+\s+(.+)$', output, re.MULTILINE)
    heading_counts = {}
    for heading in headings:
        heading_lower = heading.lower().strip()
        heading_counts[heading_lower] = heading_counts.get(heading_lower, 0) + 1
    
    duplicates = [h for h, count in heading_counts.items() if count > 1]
    if duplicates:
        violations.append(f"Duplicated sections found: {', '.join(duplicates[:3])}")
    
    if violations:
        return False, "; ".join(violations)
    
    return True, None


def check_gate_e_domain_completeness(output: str, query: str) -> Tuple[bool, Optional[str]]:
    """
    Gate E: Domain Completeness Gate (when detectable)
    When the domain is identifiable, include its minimum checklist.
    
    Examples:
    - Incident management: measurable severity criteria + escalation triggers + comms templates + roles/RACI
    - Code deliverable: runnable code + install/run steps + tests if requested
    
    Returns:
        (passed, violation_message)
    """
    query_lower = query.lower()
    output_lower = output.lower()
    violations = []
    
    # Detect domain and check for required elements
    
    # Incident management domain
    if any(term in query_lower for term in ['incident', 'severity', 'p1', 'p2', 'p3', 'on-call', 'escalation']):
        required_elements = {
            'severity': ['p1', 'p2', 'p3', 'severity', 'priority'],
            'escalation': ['escalation', 'mtta', 'mttr'],
            'comms': ['communication', 'template', 'stakeholder'],
            'roles': ['role', 'raci', 'ic', 'engineer', 'manager']
        }
        
        for element_type, keywords in required_elements.items():
            found = any(keyword in output_lower for keyword in keywords)
            if not found:
                violations.append(f"Incident management domain: missing {element_type} section")
    
    # Code deliverable domain
    elif any(term in query_lower for term in ['code', 'function', 'script', 'file', 'implement', 'build']):
        required_elements = {
            'code': ['```', 'def ', 'class ', 'function'],
            'steps': ['install', 'run', 'execute', 'usage', 'how to'],
        }
        
        for element_type, keywords in required_elements.items():
            found = any(keyword in output_lower for keyword in keywords)
            if not found:
                violations.append(f"Code deliverable domain: missing {element_type} section")
    
    # If domain detected and violations found
    if violations:
        return False, "; ".join(violations)
    
    return True, None


def validate_all_gates(
    output: str,
    user_message: str,
    lexicon_lock: Optional[Dict[str, List[str]]] = None,
    output_contract: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[str]]:
    """
    Run all quality gates and return results.
    
    Returns:
        (all_passed, list_of_violations)
    """
    violations = []
    
    # Gate A: Greeting
    passed, violation = check_gate_a_greeting(output, user_message)
    if not passed:
        violations.append(f"Gate A (Greeting): {violation}")
    
    # Gate B: Lexicon
    passed, violation = check_gate_b_lexicon(output, lexicon_lock)
    if not passed:
        violations.append(f"Gate B (Lexicon): {violation}")
    
    # Gate C: Output Contract
    passed, violation = check_gate_c_output_contract(output, output_contract)
    if not passed:
        violations.append(f"Gate C (Output Contract): {violation}")
    
    # Gate D: Completeness
    passed, violation = check_gate_d_completeness(output)
    if not passed:
        violations.append(f"Gate D (Completeness): {violation}")
    
    # Gate E: Domain Completeness
    passed, violation = check_gate_e_domain_completeness(output, user_message)
    if not passed:
        violations.append(f"Gate E (Domain Completeness): {violation}")
    
    all_passed = len(violations) == 0
    return all_passed, violations

