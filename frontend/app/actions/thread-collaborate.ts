"use server"

/**
 * Server Actions for Thread-based Collaboration
 * 
 * These actions call the new /api/threads/:threadId/collaborate endpoint
 * that returns the structured response with internal pipeline + external reviews.
 */

import {
  CollaborateRequestBody,
  CollaborateResponse
} from '@/lib/collaborate-types'

// Backend API URL (use environment variable or default)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Enhanced collaboration for a specific thread
 */
export async function threadCollaborate(
  threadId: string,
  message: string,
  mode: 'auto' | 'manual' = 'auto'
): Promise<CollaborateResponse> {
  try {
    const request: CollaborateRequestBody = {
      message,
      mode
    }

    console.log('[thread-collaborate] Starting collaboration:', {
      threadId,
      messageLength: message.length,
      mode
    })

    const response = await fetch(`${API_BASE_URL}/api/threads/${threadId}/collaborate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Org-Id': 'org_demo', // TODO: Get from auth context
      },
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      console.error('[thread-collaborate] API error:', {
        status: response.status,
        statusText: response.statusText,
        error: errorData
      })
      
      throw new Error(`Thread collaboration failed: ${response.status} ${response.statusText}`)
    }

    const result: CollaborateResponse = await response.json()

    console.log('[thread-collaborate] Success:', {
      threadId,
      internalStages: result.internal_pipeline.stages.length,
      externalReviews: result.external_reviews.length,
      finalAnswerLength: result.final_answer.content.length,
      totalModels: result.meta.models_involved.length,
      totalTime: result.meta.total_latency_ms
    })

    return result

  } catch (error) {
    console.error('[thread-collaborate] Error:', error)
    throw error
  }
}

/**
 * Get collaboration information for UI display
 */
export async function getCollaborationInfo(): Promise<{
  available_providers: string[]
  review_modes: Array<{
    mode: 'auto' | 'high_fidelity' | 'expert'
    name: string
    description: string
  }>
  default_settings: {
    enable_external_review: boolean
    review_mode: string
  }
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/collaboration/info`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Org-Id': 'org_demo',
      },
      cache: 'no-store'
    })

    if (!response.ok) {
      // Fallback to defaults if info endpoint is not available
      return {
        available_providers: ['openai', 'google', 'perplexity', 'kimi', 'openrouter'],
        review_modes: [
          {
            mode: 'auto',
            name: 'Auto',
            description: 'External review triggered automatically based on confidence'
          },
          {
            mode: 'high_fidelity',
            name: 'High Fidelity',
            description: 'Always include external multi-model review'
          },
          {
            mode: 'expert',
            name: 'Expert',
            description: 'Maximum external reviewers + comprehensive analysis'
          }
        ],
        default_settings: {
          enable_external_review: true,
          review_mode: 'auto'
        }
      }
    }

    return await response.json()
  } catch (error) {
    console.error('[thread-collaborate] Error getting collaboration info:', error)
    // Return fallback defaults
    return {
      available_providers: ['openai', 'google', 'perplexity', 'kimi', 'openrouter'],
      review_modes: [
        {
          mode: 'auto',
          name: 'Auto',
          description: 'External review triggered automatically based on confidence'
        },
        {
          mode: 'high_fidelity',
          name: 'High Fidelity',
          description: 'Always include external multi-model review'
        },
        {
          mode: 'expert',
          name: 'Expert',
          description: 'Maximum external reviewers + comprehensive analysis'
        }
      ],
      default_settings: {
        enable_external_review: true,
        review_mode: 'auto'
      }
    }
  }
}