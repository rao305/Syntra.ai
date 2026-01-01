/**
 * TypeScript types for the Dynamic Collaborate Orchestrator
 * 
 * These types mirror the backend Pydantic models for the
 * dynamic collaboration system.
 */

// ============================================================================
// Model Capabilities
// ============================================================================

export type CostTier = 'low' | 'medium' | 'high'

export interface ModelStrengths {
  reasoning: number    // 0.0 - 1.0
  creativity: number   // 0.0 - 1.0
  factuality: number   // 0.0 - 1.0
  code: number         // 0.0 - 1.0
  long_context: number // 0.0 - 1.0
}

export interface ModelCapability {
  id: string                  // Format: "provider:model-name"
  display_name: string
  provider: string
  model_name: string
  strengths: ModelStrengths
  cost_tier: CostTier
  has_browse: boolean
  relative_latency: number    // 0.0 (fastest) to 1.0 (slowest)
  max_context_tokens: number
  description: string
}

// ============================================================================
// User Settings
// ============================================================================

export type UserPriority = 'quality' | 'balanced' | 'speed' | 'cost'

export interface UserSettings {
  priority: UserPriority
  max_steps: number  // 1-7
}

// ============================================================================
// Collaboration Roles
// ============================================================================

export type CollabRole = 'analyst' | 'researcher' | 'creator' | 'critic' | 'synthesizer'

export const COLLAB_ROLE_DISPLAY: Record<CollabRole, { name: string; description: string; icon: string }> = {
  analyst: {
    name: 'Analyst',
    description: 'Clarifies and decomposes the task',
    icon: '🔍'
  },
  researcher: {
    name: 'Researcher',
    description: 'Gathers facts and references',
    icon: '📚'
  },
  creator: {
    name: 'Creator',
    description: 'Produces the draft solution',
    icon: '✨'
  },
  critic: {
    name: 'Critic',
    description: 'Evaluates and identifies issues',
    icon: '🎯'
  },
  synthesizer: {
    name: 'Synthesizer',
    description: 'Creates the final polished answer',
    icon: '🔮'
  }
}

// ============================================================================
// Collaboration Plan
// ============================================================================

export interface CollabStep {
  step_index: number
  role: CollabRole
  model_id: string
  model_name?: string
  purpose: string
  instructions_for_step?: string
  needs_previous_steps: string[]
  estimated_importance: number  // 0.0 - 1.0
  model_rationale: string
}

export interface CollaborationPlan {
  pipeline_summary: string
  steps: CollabStep[]
  planning_time_ms: number
}

// ============================================================================
// Step Results
// ============================================================================

export interface StepResult {
  step_index: number
  role: CollabRole
  model_id: string
  model_name: string
  purpose: string
  content: string
  execution_time_ms: number
  success: boolean
  error?: string
}

// ============================================================================
// External Review Types (Multi-Model Council)
// ============================================================================

export interface ExternalReview {
  reviewer: string
  provider: string
  model: string
  critique: string
  status: 'success' | 'failed'
  error?: string
}

export interface SynthesisMetadata {
  synthesis_type: 'minimal_changes' | 'moderate_integration' | 'major_revision' | 'uncertainty_highlighted'
  primary_improvement: 'factual_correction' | 'perspective_added' | 'clarity_enhanced' | 'uncertainty_noted'
  confidence_level: 'high' | 'medium' | 'low'
  synthesis_status: 'success' | 'failed'
  analysis_available: boolean
  fallback_used?: boolean
  error?: string
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface DynamicCollaborateRequest {
  user_id?: string
  message: string
  thread_id?: string
  thread_context?: string
  settings?: UserSettings
}

export interface DynamicCollaborateResponse {
  turn_id: string
  final_answer: string
  plan: CollaborationPlan
  step_results: StepResult[]
  total_time_ms: number
  available_models_used: string[]
}

export interface EnhancedCollaborateRequest {
  user_id?: string
  message: string
  conversation_id?: string
  enable_external_review?: boolean
  review_mode?: 'auto' | 'high_fidelity' | 'expert'
}

export interface EnhancedCollaborateResponse {
  collab_run: {
    id: string
    conversation_id: string
    status: string
    total_time_ms: number
  }
  internal_report: string
  compressed_report?: string
  external_critiques: ExternalReview[]
  final_answer: string
  synthesis_metadata?: SynthesisMetadata
  external_review_conducted: boolean
  reviewers_consulted: number
  total_time_ms: number
}

export interface AvailableModelsResponse {
  models: ModelCapability[]
  total_count: number
}

// ============================================================================
// Streaming Types
// ============================================================================

export type StreamEventType = 
  | 'planning'
  | 'plan_created'
  | 'step_started'
  | 'step_completed'
  | 'final_answer'
  | 'error'
  | 'done'

export interface StreamEventPlanning {
  type: 'planning'
  message: string
}

export interface StreamEventPlanCreated {
  type: 'plan_created'
  plan: {
    pipeline_summary: string
    steps: {
      step_index: number
      role: CollabRole
      model_id: string
      purpose: string
    }[]
    planning_time_ms: number
  }
}

export interface StreamEventStepStarted {
  type: 'step_started'
  step_index: number
  role: CollabRole
  model_id: string
}

export interface StreamEventStepCompleted {
  type: 'step_completed'
  step_index: number
  role: CollabRole
  content?: string
  execution_time_ms?: number
  success: boolean
  error?: string
}

export interface StreamEventFinalAnswer {
  type: 'final_answer'
  turn_id: string
  content: string
}

export interface StreamEventError {
  type: 'error'
  message: string
}

export interface StreamEventDone {
  type: 'done'
}

export type StreamEvent =
  | StreamEventPlanning
  | StreamEventPlanCreated
  | StreamEventStepStarted
  | StreamEventStepCompleted
  | StreamEventFinalAnswer
  | StreamEventError
  | StreamEventDone

// ============================================================================
// Helper Functions
// ============================================================================

export function getProviderFromModelId(modelId: string): string {
  const [provider] = modelId.split(':')
  return provider
}

export function getModelNameFromModelId(modelId: string): string {
  const [, ...rest] = modelId.split(':')
  return rest.join(':')
}

export function formatExecutionTime(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`
  }
  return `${(ms / 1000).toFixed(1)}s`
}

export function getRoleColor(role: CollabRole): string {
  const colors: Record<CollabRole, string> = {
    analyst: '#3B82F6',    // Blue
    researcher: '#8B5CF6', // Purple
    creator: '#10B981',    // Green
    critic: '#F59E0B',     // Amber
    synthesizer: '#EC4899' // Pink
  }
  return colors[role]
}

/**
 * Default settings for collaboration
 */
export const DEFAULT_COLLAB_SETTINGS: UserSettings = {
  priority: 'balanced',
  max_steps: 5
}

/**
 * Default settings for enhanced collaboration
 */
export const DEFAULT_ENHANCED_COLLAB_SETTINGS = {
  enable_external_review: true,
  review_mode: 'auto' as const
}

// ============================================================================
// Enhanced Collaboration Helper Functions
// ============================================================================

export function getReviewModeDisplay(mode: 'auto' | 'high_fidelity' | 'expert'): { name: string; description: string } {
  const displays = {
    auto: {
      name: 'Auto',
      description: 'External review triggered automatically based on confidence'
    },
    high_fidelity: {
      name: 'High Fidelity',
      description: 'Always include external multi-model review'
    },
    expert: {
      name: 'Expert',
      description: 'Maximum external reviewers + comprehensive analysis'
    }
  }
  return displays[mode]
}

export function getSynthesisTypeDisplay(type: SynthesisMetadata['synthesis_type']): { name: string; description: string; color: string } {
  const displays = {
    minimal_changes: {
      name: 'Minimal Changes',
      description: 'External reviews mostly agreed with internal report',
      color: '#10B981' // Green
    },
    moderate_integration: {
      name: 'Moderate Integration',
      description: 'Some external suggestions were incorporated',
      color: '#3B82F6' // Blue
    },
    major_revision: {
      name: 'Major Revision',
      description: 'Significant changes based on external feedback',
      color: '#F59E0B' // Amber
    },
    uncertainty_highlighted: {
      name: 'Uncertainty Highlighted',
      description: 'Major disagreements or knowledge gaps identified',
      color: '#EF4444' // Red
    }
  }
  return displays[type]
}

export function getReviewerIcon(provider: string): string {
  const icons: Record<string, string> = {
    perplexity: '🔍',
    gemini: '🎯',
    openai: '✨',
    kimi: '🌙',
    openrouter: '🔀'
  }
  return icons[provider] || '🤖'
}

export function formatReviewerName(reviewer: string, provider: string): string {
  // Clean up reviewer names for display
  const cleanNames: Record<string, string> = {
    'Factual Expert': '🔍 Factual Expert',
    'Perspective Analyst': '🎯 Perspective Analyst',
    'Clarity Specialist': '✨ Clarity Specialist',
    'Alternative Perspective': '🌙 Alternative Perspective',
    'Technical Depth': '🔀 Technical Depth',
    'Systematic Analysis': '🔀 Systematic Analysis'
  }
  return cleanNames[reviewer] || `${getReviewerIcon(provider)} ${reviewer}`
}












