/**
 * QueryRouter: Intelligent routing based on query content
 * 
 * Analyzes user queries and routes to the most appropriate LLM provider
 * based on domain specialization and query characteristics.
 * 
 * This mirrors the Python backend's analyze_content() logic.
 */

export type ProviderType = "openai" | "anthropic" | "gemini" | "perplexity";

export interface RoutingDecision {
  provider: ProviderType;
  model: string;
  reason: string;
}

/**
 * Analyze query content and determine the best provider/model
 * 
 * Routing logic based on domain specialization:
 * - Gemini: Code generation, technical execution, long context
 * - OpenAI: Complex reasoning, creative tasks, social chat
 * - Perplexity: Real-time information, factual Q&A, web search
 * - Anthropic: (Future: advanced reasoning, safety-critical)
 */
export function analyzeContent(
  message: string,
  contextSize: number = 0
): RoutingDecision {
  const messageLower = message.toLowerCase();

  // ═══════════════════════════════════════════════════════════════════
  // DOMAIN 0: SOCIAL GREETINGS (OpenAI Agent) - CHECK FIRST!
  // ═══════════════════════════════════════════════════════════════════
  const socialGreetings = [
    "hello", "hi", "hey", "greetings", "good morning", "good afternoon",
    "good evening", "how are you", "what's up", "howdy"
  ];
  if (socialGreetings.some(greeting => messageLower.includes(greeting))) {
    return {
      provider: "openai",
      model: "gpt-4o-mini",
      reason: "Social greeting (OpenAI GPT-4o-mini - conversational, no citations)"
    };
  }

  // ═══════════════════════════════════════════════════════════════════
  // DOMAIN 1: TECHNICAL EXECUTION (Gemini Agent)
  // ═══════════════════════════════════════════════════════════════════
  // Specialization: Code generation, algorithms, data structures, debugging
  const codeKeywords = [
    "json", "code", "function", "class", "api", "tool", "call",
    "format", "parse", "extract", "schema", "structure", "plan",
    "automate", "workflow", "execute", "generate code", "write script",
    "create function", "build api", "implement", "develop",
    // Programming languages
    "python", "javascript", "java", "c++", "rust", "go", "typescript",
    "ruby", "php", "swift", "kotlin", "scala", "html", "css", "sql",
    // Code-related actions
    "algorithm", "program", "script", "write a", "write an", "create a",
    "build a", "make a", "debug", "refactor", "optimize code"
  ];
  if (codeKeywords.some(keyword => messageLower.includes(keyword))) {
    return {
      provider: "gemini",
      model: "gemini-1.5-flash",
      reason: "Code generation (Gemini 1.5 Flash - fast, 60 RPM)"
    };
  }

  // ═══════════════════════════════════════════════════════════════════
  // DOMAIN 2: COMPLEX REASONING (OpenAI Agent)
  // ═══════════════════════════════════════════════════════════════════
  // Specialization: Multi-step logic, analysis, creative writing, mathematics
  const reasoningKeywords = [
    "analyze", "compare", "contrast", "evaluate", "assess", "critique",
    "explain", "why", "reason", "logic", "think", "solve",
    "calculate", "math", "equation", "proof", "theorem",
    "creative", "write a story", "poem", "essay", "article",
    "brainstorm", "ideate", "design thinking", "strategy",
    "multi-step", "complex", "detailed analysis", "deep dive"
  ];
  if (reasoningKeywords.some(keyword => messageLower.includes(keyword))) {
    return {
      provider: "openai",
      model: "gpt-4o-mini",
      reason: "Complex reasoning (GPT-4o-mini - superior logic)"
    };
  }

  // ═══════════════════════════════════════════════════════════════════
  // DOMAIN 3: REAL-TIME INFORMATION (Perplexity Agent)
  // ═══════════════════════════════════════════════════════════════════
  // Specialization: Current events, news, citations, web-grounded facts
  const researchKeywords = [
    "latest", "recent", "news", "current", "today", "now",
    "what is happening", "cite", "source", "research",
    "latest news", "breaking", "update", "discover", "investigate",
    "analyze trends", "market research", "competitive analysis",
    "events", "happening", "developments", "situation", "status",
    "web search", "google", "look up"
  ];
  if (researchKeywords.some(keyword => messageLower.includes(keyword))) {
    return {
      provider: "perplexity",
      model: "sonar",
      reason: "Real-time research (Perplexity Sonar - live web search)"
    };
  }

  // ═══════════════════════════════════════════════════════════════════
  // DOMAIN 4: LONG CONTEXT (Gemini Agent)
  // ═══════════════════════════════════════════════════════════════════
  // Specialization: Large documents, codebases, long conversations
  if (contextSize > 10) {
    return {
      provider: "gemini",
      model: "gemini-1.5-pro",
      reason: `Long conversation (${contextSize} msgs - Gemini 1.5 Pro, 2M tokens)`
    };
  }

  const longDocKeywords = [
    "pdf", "document", "file", "codebase", "repository",
    "long", "entire", "whole", "full text", "analyze document",
    "summarize", "extract from", "process document", "parse file",
    "codebase analysis", "repository analysis"
  ];
  if (longDocKeywords.some(keyword => messageLower.includes(keyword))) {
    return {
      provider: "gemini",
      model: "gemini-1.5-pro",
      reason: "Document analysis (Gemini 1.5 Pro - 2M token context)"
    };
  }

  // ═══════════════════════════════════════════════════════════════════
  // DOMAIN 5: FACTUAL QUESTIONS (Perplexity Agent)
  // ═══════════════════════════════════════════════════════════════════
  // Specialization: Factual Q&A with citations
  const questionPatterns = [
    /\?$/,  // Ends with question mark
    /^(what|who|where|when|why|how|which|can|could|should|would)/,  // Question words
    /(tell me|explain|describe|define|compare|contrast|list|identify)/,  // Question verbs
    /(what is|what are|how does|how do|why is|why are)/  // Common question phrases
  ];
  const isQuestion = questionPatterns.some(pattern => pattern.test(messageLower));
  
  // Skip ambiguous/philosophical questions (route to OpenAI instead)
  const ambiguousKeywords = [
    "meaning of life", "universe and everything", "make me a sandwich",
    "philosophical", "existential", "abstract", "remind me"
  ];
  const isAmbiguous = ambiguousKeywords.some(keyword => messageLower.includes(keyword));
  
  if (isQuestion && !isAmbiguous) {
    return {
      provider: "perplexity",
      model: "sonar-pro",
      reason: "Factual question (Perplexity Sonar Pro - precise with citations)"
    };
  }

  if (isAmbiguous) {
    return {
      provider: "gemini",
      model: "gemini-1.5-flash",
      reason: "Ambiguous query (Gemini 1.5 Flash - handles vague requests)"
    };
  }

  // ═══════════════════════════════════════════════════════════════════
  // DOMAIN 6: GENERAL FALLBACK (Perplexity Agent)
  // ═══════════════════════════════════════════════════════════════════
  // Default: General chat with web-grounded responses
  return {
    provider: "perplexity",
    model: "sonar",
    reason: "General chat (Perplexity Sonar - web-grounded)"
  };
}








