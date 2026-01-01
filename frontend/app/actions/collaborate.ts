"use server"

/**
 * Server Actions for Dynamic Collaboration
 * 
 * These actions interface with the backend's dynamic orchestrator,
 * which uses an LLM to plan and execute multi-agent collaboration.
 */

import {
  DynamicCollaborateRequest,
  DynamicCollaborateResponse,
  CollaborationPlan,
  AvailableModelsResponse,
  UserSettings,
  DEFAULT_COLLAB_SETTINGS,
  StreamEvent
} from '@/lib/orchestrator-types'

// Backend API URL (use environment variable or default)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Get available models for collaboration based on configured API keys
 */
export async function getAvailableModels(): Promise<AvailableModelsResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dynamic-collaborate/available-models`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Org-Id': 'org_demo', // TODO: Get from auth context
      },
      cache: 'no-store'
    })

    if (!response.ok) {
      console.error('[collaborate] Failed to get available models:', response.status)
      return { models: [], total_count: 0 }
    }

    return await response.json()
  } catch (error) {
    console.error('[collaborate] Error getting available models:', error)
    return { models: [], total_count: 0 }
  }
}

/**
 * Create a collaboration plan without executing it (preview)
 */
export async function createCollaborationPlan(
  message: string,
  threadContext?: string,
  settings?: Partial<UserSettings>
): Promise<CollaborationPlan | null> {
  try {
    const request: DynamicCollaborateRequest = {
      message,
      thread_context: threadContext,
      settings: {
        ...DEFAULT_COLLAB_SETTINGS,
        ...settings
      }
    }

    const response = await fetch(`${API_BASE_URL}/api/dynamic-collaborate/plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Org-Id': 'org_demo',
      },
      body: JSON.stringify(request),
      cache: 'no-store'
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[collaborate] Failed to create plan:', response.status, errorText)
      return null
    }

    return await response.json()
  } catch (error) {
    console.error('[collaborate] Error creating plan:', error)
    return null
  }
}

/**
 * Run a complete dynamic collaboration
 * 
 * This will:
 * 1. Use an LLM to plan the collaboration pipeline
 * 2. Dynamically select the best model for each role
 * 3. Execute each step in sequence
 * 4. Return the final synthesized answer
 */
export async function runDynamicCollaboration(
  message: string,
  threadId?: string,
  threadContext?: string,
  settings?: Partial<UserSettings>
): Promise<DynamicCollaborateResponse | { error: string }> {
  try {
    const request: DynamicCollaborateRequest = {
      message,
      thread_id: threadId,
      thread_context: threadContext,
      settings: {
        ...DEFAULT_COLLAB_SETTINGS,
        ...settings
      }
    }

    console.log('[collaborate] Starting dynamic collaboration:', {
      messagePreview: message.substring(0, 100),
      settings: request.settings
    })

    const response = await fetch(`${API_BASE_URL}/api/dynamic-collaborate/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Org-Id': 'org_demo',
      },
      body: JSON.stringify(request),
      cache: 'no-store'
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[collaborate] Collaboration failed:', response.status, errorText)
      
      try {
        const errorJson = JSON.parse(errorText)
        return { error: errorJson.detail || 'Collaboration failed' }
      } catch {
        return { error: `Collaboration failed: ${response.status}` }
      }
    }

    const result: DynamicCollaborateResponse = await response.json()

    console.log('[collaborate] Collaboration completed:', {
      turnId: result.turn_id,
      totalTime: `${result.total_time_ms}ms`,
      stepsCompleted: result.step_results.length,
      modelsUsed: result.available_models_used
    })

    return result
  } catch (error) {
    console.error('[collaborate] Error running collaboration:', error)
    return { 
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
}

/**
 * Type guard to check if result is an error
 */
export function isCollaborationError(
  result: DynamicCollaborateResponse | { error: string }
): result is { error: string } {
  return 'error' in result
}

/**
 * Run dynamic collaboration with streaming updates
 * 
 * Returns an async generator that yields StreamEvent objects
 * as the collaboration progresses.
 */
export async function* runDynamicCollaborationStream(
  message: string,
  threadId?: string,
  threadContext?: string,
  settings?: Partial<UserSettings>
): AsyncGenerator<StreamEvent, void, unknown> {
  const request: DynamicCollaborateRequest = {
    message,
    thread_id: threadId,
    thread_context: threadContext,
    settings: {
      ...DEFAULT_COLLAB_SETTINGS,
      ...settings
    }
  }

  console.log('[collaborate-stream] Starting streaming collaboration')

  try {
    const response = await fetch(`${API_BASE_URL}/api/dynamic-collaborate/run/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Org-Id': 'org_demo',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      yield { type: 'error', message: `Request failed: ${response.status}` }
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      yield { type: 'error', message: 'No response body' }
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      
      // Process complete SSE messages
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          try {
            const event: StreamEvent = JSON.parse(data)
            yield event
            
            if (event.type === 'done') {
              return
            }
          } catch (e) {
            console.warn('[collaborate-stream] Failed to parse SSE data:', data)
          }
        }
      }
    }
  } catch (error) {
    console.error('[collaborate-stream] Error:', error)
    yield { 
      type: 'error', 
      message: error instanceof Error ? error.message : 'Stream error'
    }
  }
}

/**
 * Get all model capabilities (regardless of API key availability)
 */
export async function getModelCapabilities(): Promise<AvailableModelsResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dynamic-collaborate/capabilities`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store'
    })

    if (!response.ok) {
      console.error('[collaborate] Failed to get capabilities:', response.status)
      return { models: [], total_count: 0 }
    }

    return await response.json()
  } catch (error) {
    console.error('[collaborate] Error getting capabilities:', error)
    return { models: [], total_count: 0 }
  }
}

// ============================================================================
// Helper Functions for Integration with Existing Workflow
// ============================================================================

/**
 * Convert dynamic collaboration result to workflow-compatible format
 * 
 * This allows the dynamic orchestrator to work with the existing
 * workflow UI components.
 */
export function convertToWorkflowSteps(result: DynamicCollaborateResponse) {
  return result.step_results.map(step => ({
    id: `step-${step.step_index}`,
    role: step.role,
    model: step.model_id.split(':')[0] as 'gpt' | 'gemini' | 'perplexity' | 'kimi',
    mode: 'auto' as const,
    status: step.success ? 'done' as const : 'error' as const,
    inputContext: '',
    outputDraft: step.content,
    outputFinal: step.content,
    metadata: {
      isMock: false,
      providerName: step.model_name,
      executionTime: step.execution_time_ms,
      modelRationale: step.purpose
    },
    error: step.error ? {
      message: step.error,
      provider: step.model_id,
      type: 'network' as const
    } : undefined
  }))
}

/**
 * Get a brief summary of the collaboration for display
 */
export function getCollaborationSummary(result: DynamicCollaborateResponse) {
  const successfulSteps = result.step_results.filter(s => s.success).length
  const totalSteps = result.step_results.length
  const totalTimeSeconds = (result.total_time_ms / 1000).toFixed(1)
  
  return {
    stepsCompleted: `${successfulSteps}/${totalSteps}`,
    totalTime: `${totalTimeSeconds}s`,
    modelsUsed: result.available_models_used.length,
    planSummary: result.plan.pipeline_summary,
    roles: result.step_results.map(s => ({
      role: s.role,
      model: s.model_name,
      success: s.success
    }))
  }
}












