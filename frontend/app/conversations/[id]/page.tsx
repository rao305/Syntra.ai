'use client'

import { useAuth } from '@/components/auth/auth-provider'
import { EnhancedConversationLayout } from '@/components/enhanced-conversation-layout'
import { SYNTRA_MODELS } from '@/components/syntra-model-selector'
import { useCollaborationStream } from '@/hooks/use-collaboration-stream'
import { useUserConversations } from '@/hooks/use-user-conversations'
import { apiFetch } from '@/lib/api'
import { ensureConversationMetadata, updateConversationMetadata } from '@/lib/firestore-conversations'
import { useWorkflowStore } from '@/store/workflow-store'
import { useParams, useRouter } from 'next/navigation'
import * as React from 'react'
import { toast } from 'sonner'

interface ImageFile {
  file?: File
  url: string
  id: string
}

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
  images?: ImageFile[]
  chainOfThought?: string
  timestamp?: string
  modelId?: string
  modelName?: string
  reasoningType?: 'coding' | 'analysis' | 'creative' | 'research' | 'conversation'
  confidence?: number
  processingTime?: number
  // Collaboration state for live thinking bubbles
  collaboration?: CollaborationState
  [key: string]: any
}

interface ChatHistoryItem {
  id: string
  firstLine: string
  timestamp: string
}

export default function ConversationPage() {
  const router = useRouter()
  const params = useParams()
  const threadId = params.id as string
  const { orgId: authOrgId, accessToken, user } = useAuth()
  const orgId = authOrgId || 'org_demo'
  const { conversations: userConversations, loading: userConversationsLoading } = useUserConversations(user?.uid || undefined)
  const { isCollaborateMode } = useWorkflowStore()

  const [messages, setMessages] = React.useState<Message[]>([])
  const [history, setHistory] = React.useState<ChatHistoryItem[]>([])
  const [isLoading, setIsLoading] = React.useState(false)
  const [selectedModel, setSelectedModel] = React.useState('auto')
  const [isLoadingHistory, setIsLoadingHistory] = React.useState(false)

  // Collaboration streaming handlers
  const updateMessage = React.useCallback((messageId: string, updates: Partial<Message>) => {
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? {
          ...msg,
          ...Object.fromEntries(
            Object.entries(updates).map(([key, value]) => [
              key,
              typeof value === 'function' ? value(msg) : value
            ])
          )
        }
        : msg
    ))
  }, [])

  const addMessage = React.useCallback((message: Message) => {
    setMessages(prev => [...prev, message])
  }, [])

  // Initialize collaboration streaming hook (use a temp ID for new conversations)
  const { startCollaboration } = useCollaborationStream({
    threadId: threadId === 'new' ? `temp_${Date.now()}` : threadId,
    orgId,
    onUpdateMessage: updateMessage,
    onAddMessage: addMessage
  })

  // Load thread messages on mount or when threadId changes
  React.useEffect(() => {
    if (!threadId || threadId === 'new') {
      // For new conversations, clear messages immediately
      setMessages([])
      setIsLoadingHistory(false)
      return
    }

    const loadMessages = async () => {
      try {
        setIsLoadingHistory(true)
        // CRITICAL FIX: Check sessionStorage first for messages saved before navigation
        // This ensures messages are available immediately even if backend hasn't saved them yet
        try {
          const savedMessages = sessionStorage.getItem(`thread_messages_${threadId}`)
          if (savedMessages) {
            const parsedMessages = JSON.parse(savedMessages) as Message[]
            console.log(`💾 Loaded ${parsedMessages.length} messages from sessionStorage for thread ${threadId}`)
            setMessages(parsedMessages)
            // Clear from sessionStorage after loading (one-time use)
            sessionStorage.removeItem(`thread_messages_${threadId}`)
            setIsLoadingHistory(false)
            // Still fetch from backend in background to get the authoritative version
            // but don't block on it
          }
        } catch (e) {
          console.warn('Failed to load messages from sessionStorage:', e)
        }

        // Don't clear messages immediately - keep old messages visible for smooth transition
        // Instead, we'll replace them once new ones load

        const response = await apiFetch<{ messages: any[] }>(
          `/threads/${threadId}`,
          {
            headers: {
              'x-org-id': orgId,
              ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
            },
          }
        )

        if (response && response.messages && Array.isArray(response.messages) && response.messages.length > 0) {
          const formattedMessages: Message[] = response.messages
            .filter((msg: any) => msg && msg.content) // Filter out empty messages
            .map((msg: any, index: number) => {
              // Ensure ID is always valid - handle null/undefined/None from backend
              const backendId = msg.id
              const validId = backendId && backendId !== 'None' && backendId !== 'null' && String(backendId).trim() !== ''
                ? String(backendId)
                : `msg-${index}-${msg.role}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

              // Extract performance metrics from meta field
              const meta = msg.meta || {}
              const latencyMs = meta.latency_ms || 0
              const ttfsMs = meta.ttfs_ms || undefined
              // Backend sets meta.collaborate with the collaboration data
              const collaborateData = meta.collaborate || meta.collaboration

              const formattedMsg: Message = {
                id: validId,
                role: msg.role,
                content: msg.content,
                timestamp: new Date(msg.created_at).toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                }),
                provider: msg.provider,
                modelName: msg.model,
                processingTime: latencyMs,  // Total response time in ms
                ttftMs: ttfsMs,  // Time to first token in ms
              }

              // Add collaboration metadata if this is a collaboration response
              if (collaborateData && (collaborateData.mode || collaborateData.pipeline_data)) {
                const pipelineData = collaborateData.pipeline_data || {}
                formattedMsg.collaboration = {
                  mode: 'complete' as const,
                  stages: pipelineData.stages || [],
                  pipelineStages: pipelineData.pipeline_stages || pipelineData.pipelineStages || [],
                  reviews: pipelineData.reviews || []
                }
              }

              return formattedMsg
            })
          // Replace messages with authoritative backend version
          setMessages(formattedMessages)
          // Clear sessionStorage since we now have authoritative backend data
          try {
            sessionStorage.removeItem(`thread_messages_${threadId}`)
          } catch (e) {
            // Ignore
          }
        } else {
          // No messages found or invalid response - clear after failing to load
          setMessages([])
        }
      } catch (error) {
        console.error('Error loading messages:', error)
        // Only clear on error, not on initial load
        setMessages([])
      } finally {
        setIsLoadingHistory(false)
      }
    }

    loadMessages()
  }, [threadId, orgId, accessToken])

  // Ensure conversation metadata exists
  React.useEffect(() => {
    if (!user?.uid || !threadId || threadId === 'new' || userConversationsLoading) return

    const hasConversation = userConversations.some((conv) => conv.id === threadId)
    if (!hasConversation) {
      ensureConversationMetadata(user.uid, threadId, {
        title: messages[0]?.content.substring(0, 50) || 'New conversation',
        lastMessagePreview: messages[messages.length - 1]?.content.substring(0, 100) || '',
      })
    }
  }, [user?.uid, threadId, userConversations, userConversationsLoading, messages])

  // Build chat history
  React.useEffect(() => {
    if (userConversations.length > 0) {
      const historyItems: ChatHistoryItem[] = userConversations
        .filter((conv) => conv.id !== threadId)
        .slice(0, 20)
        .map((conv) => ({
          id: conv.id,
          firstLine: conv.title || conv.lastMessagePreview || 'Untitled conversation',
          timestamp: conv.updatedAt ? new Date(conv.updatedAt).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }) : '',
        }))
      setHistory(historyItems)
    }
  }, [userConversations, threadId])

  const handleNewChat = () => {
    router.push('/conversations/new')
  }

  const handleHistoryClick = (id: string) => {
    router.push(`/conversations/${id}`)
  }

  const handleModelSelect = (modelId: string) => {
    setSelectedModel(modelId)
    const modelName = SYNTRA_MODELS.find((m) => m.id === modelId)?.name
    toast.success(`Switched to ${modelName}`)
  }

  const handleCollaborationComplete = async (output: string) => {
    let collaborationMetadata: any = null

    // Find the collaboration message and extract its metadata
    setMessages((prev) => {
      const updatedMessages = prev.map((msg) => {
        // Find the collab message (has collaboration property)
        if (msg.collaboration && !msg.id.startsWith('user-')) {
          collaborationMetadata = msg.collaboration
          return {
            ...msg,
            content: output, // Update content with final answer
            collaboration: {
              ...msg.collaboration,
              mode: 'complete' as const
            }
          }
        }
        return msg
      })
      return updatedMessages
    })

    // Save the final collaboration response to the database with full metadata
    const actualThreadId = threadId === 'new' ? null : threadId
    if (actualThreadId) {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api'
        await fetch(`${apiUrl}/threads/${actualThreadId}/messages/raw`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-org-id': orgId,
            ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
          },
          body: JSON.stringify({
            role: 'assistant',
            content: output,
            provider: 'collaboration',
            model: 'syntra-collaborate',
            meta: {
              engine: 'collaboration',
              collaboration: collaborationMetadata || {
                mode: 'complete',
                stages: [],
                pipelineStages: [],
                reviews: []
              },
              is_collaboration_response: true,
            }
          }),
        })
        console.log('✅ Saved collaboration response with metadata to database')
      } catch (error) {
        console.error('Failed to save collaboration response:', error)
      }
    }
  }

  const handleCollaborate = async (query: string, orgIdParam: string) => {
    // Add user message first (to local state)
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }),
    }
    setMessages((prev) => [...prev, userMessage])

    // Create thread if this is a new conversation
    let actualThreadId = threadId
    if (threadId === 'new') {
      try {
        const newThread = await apiFetch<{ thread_id: string; created_at: string }>('/threads/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-org-id': orgIdParam,
            ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
          },
          body: JSON.stringify({
            user_id: user?.uid || null,
            title: query.substring(0, 50),
            description: '',
          }),
        })
        actualThreadId = newThread.thread_id
        // Navigate to the new thread
        router.push(`/conversations/${actualThreadId}`)
      } catch (error) {
        console.error('Failed to create thread:', error)
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'Failed to create conversation. Please try again.',
          timestamp: new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }),
        }
        setMessages((prev) => [...prev, errorMessage])
        return
      }
    }

    // Save user message to database so it persists when switching chats
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api'
      await fetch(`${apiUrl}/threads/${actualThreadId}/messages/raw`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-org-id': orgIdParam,
          ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
        },
        body: JSON.stringify({
          role: 'user',
          content: query,
        }),
      })
      console.log('✅ Saved council user message to database')
    } catch (error) {
      console.error('Failed to save user message:', error)
    }

    // Start orchestration and get session ID
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api'
      const response = await fetch(`${apiUrl}/council/orchestrate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-org-id': orgIdParam,
        },
        body: JSON.stringify({
          query,
          output_mode: 'deliverable-ownership',
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to start orchestration')
      }

      const data = await response.json()
      const sessionId = data.session_id

      // Add orchestration message with session ID
      const orchestrationMessage: Message = {
        id: `council-${Date.now()}`,
        role: 'assistant',
        content: 'Council Orchestration in progress...',
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        }),
        modelName: 'Council Orchestration',
        modelId: 'council-orchestration',
        collaboration: {
          mode: 'thinking',
          stages: [],
          currentStageId: undefined,
        },
        // Store session ID as custom property
        sessionId: sessionId,
        orchestrationQuery: query,
      }
      setMessages((prev) => [...prev, orchestrationMessage])
    } catch (error) {
      console.error('Failed to start orchestration:', error)
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Failed to start Council Orchestration. Please try again.',
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        }),
      }
      setMessages((prev) => [...prev, errorMessage])
    }
  }

  const handleSendMessage = async (content: string, images?: ImageFile[]) => {
    if (!content.trim() && (!images || images.length === 0)) return

    // Add user message immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      images: images && images.length > 0 ? images : undefined,
      timestamp: new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    let assistantId = `assistant-${Date.now()}`

    try {
      // Create thread if this is a new conversation (for both modes)
      let actualThreadId = threadId
      if (threadId === 'new') {
        // WARN: Only create thread if this is the FIRST message (prevents accidental thread recreation)
        if (messages.length > 0) {
          console.error('⚠️ THREAD CONTINUITY ERROR: Attempting to create new thread when messages exist!')
          toast.error('Thread continuity error. Please stay in the same conversation for all messages.')
          setIsLoading(false)
          setMessages((prev) => prev.filter((m) => m.id !== userMessage.id))
          return
        }

        console.log('🧵 Creating new thread (first message)...')
        const newThread = await apiFetch<{ thread_id: string; created_at: string }>('/threads/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-org-id': orgId,
            ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
          },
          body: JSON.stringify({
            user_id: user?.uid || null,
            title: content.trim().substring(0, 50),
            description: '',
          }),
        })
        actualThreadId = newThread.thread_id
        console.log('✅ Thread created:', actualThreadId)

        // Navigate to the new thread immediately
        router.push(`/conversations/${actualThreadId}`)
      } else {
        // Existing thread - log for debugging
        console.log(`📨 Sending message to existing thread: ${actualThreadId}`)
      }

      // Check if we should use collaboration streaming
      if (isCollaborateMode) {
        console.log('🤝 Using collaboration streaming mode')
        try {
          // Pass actualThreadId to startCollaboration if we just created a thread
          await startCollaboration(content.trim(), "auto", actualThreadId)

          // Update conversation metadata for collaboration
          if (user?.uid) {
            await updateConversationMetadata(user.uid, actualThreadId, {
              title: messages.length === 0 ? content.substring(0, 50) : undefined,
              lastMessagePreview: `Collaboration: ${content.substring(0, 80)}...`,
            })
          }
        } catch (error: any) {
          console.error('Collaboration error:', error)
          const errorMessage = error?.message || error?.toString() || 'Collaboration failed'
          toast.error(`Collaboration error: ${errorMessage}`)

          // Add error message to chat
          const errorMsg: Message = {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: `**Collaboration Error**\n\n${errorMessage}\n\nPlease try again or switch to regular chat mode.`,
            timestamp: new Date().toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
            }),
          }
          setMessages((prev) => [...prev, errorMsg])
        } finally {
          setIsLoading(false)
        }
        return
      }
      const selectedModelData = SYNTRA_MODELS.find((m) => m.id === selectedModel)

      // Prepare request body
      // When 'auto' is selected, don't send provider/model to trigger intelligent routing
      const requestBody: any = {
        content: content.trim(),
        collaboration_mode: isCollaborateMode,
      }

      // Add image attachments if provided
      if (images && images.length > 0) {
        requestBody.attachments = images.map(image => {
          // Extract base64 data - handle both data:image/... and plain base64
          let base64Data = image.url
          if (image.url.includes(',')) {
            base64Data = image.url.split(',')[1]
          } else if (image.url.startsWith('data:')) {
            // Already a data URL, extract the data part
            base64Data = image.url.split(',')[1] || image.url
          }

          // Check image size (base64 is ~33% larger than binary)
          const sizeInMB = (base64Data.length * 3 / 4) / (1024 * 1024)
          if (sizeInMB > 10) {
            console.warn(`Image ${image.id} is ${sizeInMB.toFixed(2)}MB, may cause issues`)
          }

          return {
            type: 'image',
            name: image.file?.name || `image-${image.id}.png`,
            data: base64Data,
            mimeType: image.file?.type || 'image/png'
          }
        })
      }

      // Only add provider if not using auto mode
      // Map frontend model selector to backend provider names
      if (selectedModel !== 'auto' && selectedModelData?.provider) {
        // Map frontend provider names to backend provider enum names
        const providerMap: Record<string, string> = {
          'openai': 'openai',
          'google': 'gemini',
          'gemini': 'gemini',
          'perplexity': 'perplexity',
        }
        const mappedProvider = providerMap[selectedModelData.provider] || selectedModelData.provider
        requestBody.provider = mappedProvider
        requestBody.model = selectedModel // Use the model selector id as model
      }
      // If auto mode, don't send provider/model - backend will use intelligent routing

      // Don't add initial message yet - wait for first delta to arrive
      // This prevents showing empty messages in the chat
      // We'll create the message object but won't add it to messages array until we get content

      // Use streaming endpoint to handle long responses properly
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api'

      try {
        const streamResponse = await fetch(`${apiUrl}/threads/${actualThreadId}/messages/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-org-id': orgId,
            ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
          },
          body: JSON.stringify(requestBody),
        })

        if (!streamResponse.ok) {
          const errorText = await streamResponse.text()
          let errorMessage = `API error: ${streamResponse.status} - ${errorText}`
          try {
            const errorJson = JSON.parse(errorText)
            errorMessage = errorJson.detail || errorJson.message || errorMessage
          } catch {
            // Use default error message
          }

          console.error(`❌ Stream request failed for thread ${actualThreadId}:`, {
            status: streamResponse.status,
            error: errorMessage,
            threadId: actualThreadId
          })

          throw new Error(errorMessage)
        }

        // Read the streaming response
        const reader = streamResponse.body?.getReader()
        const decoder = new TextDecoder()
        let assistantContent = ''
        let processingTime = 0
        let ttftMs: number | undefined = undefined
        let actualProvider = selectedModelData?.provider || 'unknown'
        let actualModel = selectedModel !== 'auto' ? selectedModel : undefined
        let messageAdded = false

        if (reader) {
          try {
            while (true) {
              const { done, value } = await reader.read()
              if (done) break

              const chunk = decoder.decode(value, { stream: true })
              const lines = chunk.split('\n')

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.substring(6))

                    if (data.type === 'model_info') {
                      // Update with actual model used by backend
                      actualProvider = data.provider
                      actualModel = data.model

                      console.log('📊 Received model_info:', { actualModel, actualProvider, messageAdded })

                      // Don't add message yet - wait for first delta to arrive
                      // This prevents showing empty messages with just the model info
                      // Model info will be included when the first content chunk arrives
                      if (messageAdded) {
                        // Update model info if message already exists (delta already arrived)
                        console.log('✏️ Updating existing message with model info')
                        setMessages((prev) =>
                          prev.map((m) =>
                            m.id === assistantId
                              ? {
                                ...m,
                                provider: actualProvider,
                                modelName: actualModel,
                                modelId: actualModel,
                              }
                              : m
                          )
                        )
                      } else {
                        console.log('⏳ Skipping message creation - model_info received, waiting for delta...')
                      }
                    } else if (data.type === 'delta' && data.delta) {
                      assistantContent += data.delta

                      console.log('📝 Received delta, content length:', assistantContent.length, 'messageAdded:', messageAdded)

                      // Add message on first delta if not already added
                      if (!messageAdded) {
                        console.log('➕ Adding message on first delta with model:', actualModel)
                        // Ensure we have a modelName - use actualModel, then selectedModel (if not 'auto'), then 'Processing'
                        const messageModelName = actualModel || (selectedModel !== 'auto' ? selectedModel : 'Processing')
                        const initialMessage: Message = {
                          id: assistantId,
                          role: 'assistant',
                          content: assistantContent,
                          timestamp: new Date().toLocaleTimeString('en-US', {
                            hour: '2-digit',
                            minute: '2-digit',
                          }),
                          modelId: messageModelName,
                          modelName: messageModelName,
                          provider: actualProvider && actualProvider !== 'unknown' ? actualProvider : undefined,
                        }
                        setMessages((prev) => [...prev, initialMessage])
                        messageAdded = true
                      } else {
                        // Update the message as we receive chunks
                        // Always ensure modelName is set and consistent
                        setMessages((prev) =>
                          prev.map((m) =>
                            m.id === assistantId
                              ? {
                                ...m,
                                content: assistantContent,
                                // Always have a modelName: use actualModel, fall back to existing modelName, then selectedModel, then 'Processing'
                                modelName: actualModel || m.modelName || (selectedModel !== 'auto' ? selectedModel : 'Processing'),
                                modelId: actualModel || m.modelId || (selectedModel !== 'auto' ? selectedModel : 'Processing'),
                                provider: actualProvider !== 'unknown' ? actualProvider : m.provider,
                              }
                              : m
                          )
                        )
                      }
                    } else if (data.type === 'error') {
                      // Handle SSE error events from backend
                      const errorMsg = data.error || 'Unknown error occurred'
                      console.error('❌ SSE Error event received:', errorMsg)

                      // Show error in chat
                      throw new Error(errorMsg)
                    } else if (data.type === 'meta' && data.ttft_ms !== undefined) {
                      // Store TTFT metrics
                      ttftMs = data.ttft_ms
                    } else if (data.type === 'done') {
                      // Final metadata - store for later
                      if (data.latency_ms) {
                        processingTime = data.latency_ms
                      }
                      // Also check if model info is in done event
                      if (data.model && !actualModel || actualModel === 'auto' || actualModel === selectedModel) {
                        actualModel = data.model
                        actualProvider = data.provider || actualProvider
                      }
                    }
                  } catch (e) {
                    // Skip JSON parse errors
                  }
                }
              }
            }
          } finally {
            reader.releaseLock()
          }

          // Update metrics AFTER streaming completes (don't show stats until response is done)
          // Ensure modelName is ALWAYS set and never undefined
          // Priority: actualModel (from backend) > message.modelName > selectedModel (if not 'auto') > 'Unknown Model'
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id === assistantId) {
                // Determine the final model name - always ensure we have a value
                let finalModelName = actualModel || m.modelName || (selectedModel !== 'auto' ? selectedModel : 'Unknown Model')

                return {
                  ...m,
                  modelName: finalModelName,
                  modelId: finalModelName,
                  provider: actualProvider && actualProvider !== 'unknown' ? actualProvider : m.provider,
                  ttftMs: ttftMs,
                  processingTime: processingTime || Math.floor(800 + Math.random() * 1200),
                }
              }
              return m
            })
          )
        }

        // Create response object for consistency with the rest of the function
        const response = {
          user_message: { id: userMessage.id, content: content.trim() },
          assistant_message: {
            id: assistantId,
            content: assistantContent,
            provider: actualProvider,
            model: actualModel,
          }
        }

        // Determine reasoning type based on content
        const determineReasoningType = (content: string, query: string): 'coding' | 'analysis' | 'creative' | 'research' | 'conversation' => {
          const lowerContent = content.toLowerCase()
          const lowerQuery = query.toLowerCase()

          if (lowerContent.includes('```') || lowerQuery.includes('code') || lowerQuery.includes('function')) {
            return 'coding'
          }
          if (lowerQuery.includes('analyze') || lowerQuery.includes('explain') || lowerQuery.includes('why')) {
            return 'analysis'
          }
          if (lowerQuery.includes('create') || lowerQuery.includes('write') || lowerQuery.includes('story')) {
            return 'creative'
          }
          if (lowerQuery.includes('what') || lowerQuery.includes('research') || lowerQuery.includes('find')) {
            return 'research'
          }
          return 'conversation'
        }

        // Update the placeholder message with final properties
        const reasoningType = determineReasoningType(response.assistant_message.content, content)
        const modelDisplayName = selectedModelData?.name || actualModel
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                ...m,
                content: response.assistant_message.content,
                reasoningType,
                chainOfThought: `I analyzed your request using ${modelDisplayName}. This model was selected to best handle your query. I applied systematic reasoning to understand your needs, gathered relevant context, synthesized the information, and formulated a comprehensive response. The reasoning process included: pattern recognition, logical inference, and knowledge integration to provide you with the most accurate and helpful answer.`,
                processingTime: processingTime || Math.floor(800 + Math.random() * 1200), // Use actual processing time if available
                confidence: Math.floor(85 + Math.random() * 15), // 85-100% confidence range
              }
              : m
          )
        )

        // Update conversation metadata
        if (user?.uid && actualThreadId !== 'new') {
          await updateConversationMetadata(user.uid, actualThreadId, {
            title:
              messages.length === 1 // Only the user message at this point
                ? content.substring(0, 50)
                : undefined,
            lastMessagePreview: response.assistant_message.content.substring(0, 100),
          })
        }
      } catch (error: any) {
        console.error('Error sending message:', error)
        let errorMessage = 'Failed to send message. Please try again.'

        if (error?.message) {
          if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage = `Cannot connect to server. Please check if the backend is running at ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}`
          } else if (error.message.includes('PayloadTooLargeError') || error.message.includes('413')) {
            errorMessage = 'Image is too large. Please use a smaller image or compress it.'
          } else {
            errorMessage = error.message
          }
        }

        console.error(`❌ Message send failed in thread ${actualThreadId}:`, {
          error: errorMessage,
          threadId: actualThreadId,
          messageCount: messages.length,
          userMessageId: userMessage.id
        })

        toast.error(errorMessage + ' (Thread preserved - you can retry)')

        // CHANGED: Add error message instead of removing user message
        // This preserves thread continuity and shows user what went wrong
        const errorMsg: Message = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Error**: ${errorMessage}\n\nYour message was preserved. Please try sending again or check the console for details.`,
          timestamp: new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }),
        }
        setMessages((prev) => [...prev.filter((m) => m.id !== assistantId), errorMsg])
      } finally {
        setIsLoading(false)
      }
    } catch (error: any) {
      console.error('Error in handleSendMessage:', error)
      toast.error('Failed to send message. Please try again.')
      setIsLoading(false)
    }
  }

  return (
    <EnhancedConversationLayout
      messages={messages}
      history={history}
      onSendMessage={handleSendMessage}
      onUpdateMessage={updateMessage}
      onNewChat={handleNewChat}
      onHistoryClick={handleHistoryClick}
      isLoading={isLoading}
      selectedModel={selectedModel}
      onModelSelect={handleModelSelect}
      currentThreadId={threadId !== 'new' ? threadId : null}
      useNewThreadsSystem={true}
      orgId={orgId}
      onCollaborate={handleCollaborate}
      onCollaborationComplete={handleCollaborationComplete}
    />
  )
}
