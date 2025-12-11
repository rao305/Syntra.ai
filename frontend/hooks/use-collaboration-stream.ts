"use client"

import { API_BASE_URL } from '@/lib/api'
import { useCallback } from 'react'

interface CollaborationStage {
  id: string
  label: string
  status: "pending" | "active" | "done"
}

interface CollaborationState {
  mode: "thinking" | "streaming_final" | "complete"
  stages: CollaborationStage[]
  currentStageId?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  collaboration?: CollaborationState
  [key: string]: any
}

interface SSEEvent {
  type: 'stage_start' | 'stage_end' | 'final_chunk' | 'done' | 'error'
  stage_id?: string
  text?: string
  message?: any
  error?: string | { message?: string; detail?: string; error?: string }
  detail?: string
  [key: string]: any // Allow additional properties
}

interface UseCollaborationStreamProps {
  threadId: string
  orgId?: string
  onUpdateMessage: (messageId: string, updates: Partial<Message>) => void
  onAddMessage: (message: Message) => void
}

export function useCollaborationStream({
  threadId,
  orgId,
  onUpdateMessage,
  onAddMessage
}: UseCollaborationStreamProps) {

  const startCollaboration = useCallback(async (
    userMessage: string,
    mode: "auto" | "manual" = "auto",
    overrideThreadId?: string
  ) => {
    // Use override thread ID if provided (for new threads), otherwise use the hook's threadId
    const actualThreadId = overrideThreadId || threadId
    // Create initial collaboration message with thinking state
    const collaborationMessageId = `collab_${Date.now()}`

    const initialStages: CollaborationStage[] = [
      { id: "analyst", label: "Analyzing the problem…", status: "active" },
      { id: "researcher", label: "Looking up relevant information…", status: "pending" },
      { id: "creator", label: "Drafting a solution…", status: "pending" },
      { id: "critic", label: "Checking for issues…", status: "pending" },
      { id: "reviews", label: "External experts reviewing…", status: "pending" },
      { id: "director", label: "Synthesizing final answer…", status: "pending" }
    ]

    const initialMessage: Message = {
      id: collaborationMessageId,
      role: 'assistant',
      content: '',
      collaboration: {
        mode: "thinking",
        stages: initialStages,
        currentStageId: "analyst"
      },
      timestamp: new Date().toISOString(),
      modelName: 'Syntra Collaborate',
      reasoningType: 'analysis'
    }

    // Add the initial collaboration message to the chat
    onAddMessage(initialMessage)

    // Start SSE connection
    // API_BASE_URL already includes /api, so we use /collaboration instead of /api/collaboration
    const sseUrl = `${API_BASE_URL}/collaboration/${actualThreadId}/collaborate/stream`

    console.log('🔗 Starting collaboration stream:', {
      url: sseUrl,
      threadId: actualThreadId,
      orgId,
      messageLength: userMessage.length
    })

    // Include org_id in headers if available
    const headers: HeadersInit = {
      'Content-Type': 'application/json'
    }

    if (orgId) {
      headers['X-Org-ID'] = orgId
    }

    const response = await fetch(sseUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message: userMessage,
        mode: mode
      })
    })

    console.log('📡 Collaboration response:', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      headers: Object.fromEntries(response.headers.entries())
    })

    if (!response.ok) {
      let errorText = response.statusText
      try {
        const errorData = await response.json().catch(() => null)
        if (errorData) {
          errorText = errorData.detail || errorData.message || errorData.error || JSON.stringify(errorData)
        } else {
          errorText = await response.text().catch(() => response.statusText)
        }
      } catch {
        errorText = await response.text().catch(() => response.statusText)
      }
      throw new Error(`Collaboration failed: ${response.status} ${response.statusText}${errorText ? ` - ${errorText}` : ''}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('Failed to create stream reader')
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData: SSEEvent = JSON.parse(line.slice(6))
              await handleSSEEvent(collaborationMessageId, eventData)
            } catch (e) {
              console.warn('Failed to parse SSE event:', line, e)
              // If parsing fails, try to handle it as an error event
              onUpdateMessage(collaborationMessageId, {
                content: `Error parsing collaboration event: ${e instanceof Error ? e.message : 'Unknown error'}`,
                collaboration: (prevMessage: Message) => {
                  if (!prevMessage.collaboration) return undefined
                  return {
                    ...prevMessage.collaboration,
                    mode: "complete" as const
                  }
                }
              } as any)
            }
          }
        }
      }
    } catch (streamError) {
      // Handle stream errors
      const errorMsg = streamError instanceof Error
        ? streamError.message
        : typeof streamError === 'string'
          ? streamError
          : 'Collaboration stream error'
      console.error('Collaboration stream error:', streamError)
      onUpdateMessage(collaborationMessageId, {
        content: `Error: ${errorMsg}`,
        collaboration: (prevMessage: Message) => {
          if (!prevMessage.collaboration) return undefined
          return {
            ...prevMessage.collaboration,
            mode: "complete" as const
          }
        }
      } as any)
    } finally {
      reader.releaseLock()
    }
  }, [threadId, orgId, onUpdateMessage, onAddMessage])

  const handleSSEEvent = useCallback(async (
    messageId: string,
    event: SSEEvent
  ) => {
    switch (event.type) {
      case 'stage_start':
        if (event.stage_id) {
          onUpdateMessage(messageId, {
            collaboration: (prevMessage: Message) => {
              if (!prevMessage.collaboration) return undefined

              const updatedStages = prevMessage.collaboration.stages.map(stage => ({
                ...stage,
                status: stage.id === event.stage_id
                  ? "active" as const
                  : stage.status === "active"
                    ? "done" as const
                    : stage.status
              }))

              return {
                ...prevMessage.collaboration,
                stages: updatedStages,
                currentStageId: event.stage_id
              }
            }
          } as any)
        }
        break

      case 'stage_end':
        if (event.stage_id) {
          onUpdateMessage(messageId, {
            collaboration: (prevMessage: Message) => {
              if (!prevMessage.collaboration) return undefined

              const updatedStages = prevMessage.collaboration.stages.map(stage => ({
                ...stage,
                status: stage.id === event.stage_id ? "done" as const : stage.status
              }))

              return {
                ...prevMessage.collaboration,
                stages: updatedStages
              }
            }
          } as any)
        }
        break

      case 'final_chunk':
        if (event.text) {
          onUpdateMessage(messageId, {
            content: (prevMessage: Message) => (prevMessage.content || '') + event.text,
            collaboration: (prevMessage: Message) => {
              if (!prevMessage.collaboration) return undefined
              return {
                ...prevMessage.collaboration,
                mode: "streaming_final" as const
              }
            }
          } as any)
        }
        break

      case 'done':
        if (event.message) {
          // Extract pipeline data if available
          const pipelineData = (event as any).pipeline_data

          // Update to final completed state with pipeline data
          onUpdateMessage(messageId, {
            id: event.message.id,
            content: event.message.content,
            collaboration: (prevMessage: Message) => {
              if (!prevMessage.collaboration) return undefined
              return {
                ...prevMessage.collaboration,
                mode: "complete" as const,
                stages: prevMessage.collaboration.stages.map(stage => ({
                  ...stage,
                  status: "done" as const
                })),
                // Add pipeline stages and reviews for transparency
                pipelineStages: pipelineData?.stages,
                reviews: pipelineData?.reviews
              }
            },
            provider: event.message.provider,
            modelName: event.message.model || 'Syntra Collaborate'
          } as any)
        }
        break

      case 'error':
        // Handle different error formats - check all possible error locations
        let errorMessage = 'Collaboration failed'

        if (typeof event.error === 'string') {
          errorMessage = event.error
        } else if (event.error) {
          errorMessage = event.error.message || event.error.detail || event.error.error || JSON.stringify(event.error)
        } else if (event.message) {
          // Check if error is in message object
          if (typeof event.message === 'string') {
            errorMessage = event.message
          } else if (event.message.error) {
            errorMessage = typeof event.message.error === 'string'
              ? event.message.error
              : event.message.error.message || event.message.error.detail || JSON.stringify(event.message.error)
          } else if (event.message.detail) {
            errorMessage = event.message.detail
          }
        } else if (event.detail) {
          errorMessage = event.detail
        } else if (event.text) {
          // Sometimes error info might be in text field
          errorMessage = event.text
        } else {
          // If event is empty, log the full event for debugging
          console.error('Empty error event received:', JSON.stringify(event, null, 2))
          errorMessage = 'Collaboration failed - no error details provided'
        }

        // Only log full error details in development mode
        if (process.env.NODE_ENV === 'development') {
          console.warn('⚠️ Collaboration error:', errorMessage)
        }
        onUpdateMessage(messageId, {
          content: `**Collaboration Error**\n\n${errorMessage}\n\nPlease try again or switch to regular chat mode.`,
          collaboration: (prevMessage: Message) => {
            if (!prevMessage.collaboration) return undefined
            return {
              ...prevMessage.collaboration,
              mode: "complete" as const
            }
          }
        } as any)
        break

      default:
        console.warn('Unknown SSE event type:', event.type)
    }
  }, [onUpdateMessage])

  return {
    startCollaboration
  }
}