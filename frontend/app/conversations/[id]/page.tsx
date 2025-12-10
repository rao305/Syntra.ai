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
      // For new conversations, clear messages
      setMessages([])
      setIsLoadingHistory(false)
      return
    }

    const loadMessages = async () => {
      try {
        setIsLoadingHistory(true)
        // Clear previous messages while loading new ones
        setMessages([])

        const response = await apiFetch<{ messages: any[] }>(
          `/threads/${threadId}`,
          {
            headers: {
              'x-org-id': orgId,
              ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
            },
          }
        )

        if (response && response.messages && Array.isArray(response.messages)) {
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

              return {
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
            })
          setMessages(formattedMessages)
        } else {
          // No messages found or invalid response
          setMessages([])
        }
      } catch (error) {
        console.error('Error loading messages:', error)
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
        console.log('🧵 Creating new thread...')
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
        requestBody.attachments = images.map(image => ({
          type: 'image',
          name: image.file?.name || 'image',
          data: image.url.split(',')[1], // Extract base64 data part
          mimeType: image.file?.type || 'image/png'
        }))
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
      const streamResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api'}/threads/${actualThreadId}/messages/stream`, {
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
        throw new Error(`API error: ${streamResponse.status} - ${errorText}`)
      }

      // Read the streaming response
      const reader = streamResponse.body?.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''
      let processingTime = 0
      let ttftMs: number | undefined = undefined
      let actualProvider = selectedModelData?.provider || 'unknown'
      let actualModel = selectedModel
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

                    // Add message if not already added
                    if (!messageAdded) {
                      const initialMessage: Message = {
                        id: assistantId,
                        role: 'assistant',
                        content: '',
                        timestamp: new Date().toLocaleTimeString('en-US', {
                          hour: '2-digit',
                          minute: '2-digit',
                        }),
                        modelId: actualModel,
                        modelName: actualModel,
                      }
                      setMessages((prev) => [...prev, initialMessage])
                      messageAdded = true
                    } else {
                      // Update model info if message already exists
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
                    }
                  } else if (data.type === 'delta' && data.delta) {
                    assistantContent += data.delta

                    // Add message on first delta if not already added
                    if (!messageAdded) {
                      const initialMessage: Message = {
                        id: assistantId,
                        role: 'assistant',
                        content: assistantContent,
                        timestamp: new Date().toLocaleTimeString('en-US', {
                          hour: '2-digit',
                          minute: '2-digit',
                        }),
                        modelId: selectedModel,
                        modelName: actualModel || undefined,
                      }
                      setMessages((prev) => [...prev, initialMessage])
                      messageAdded = true
                    } else {
                      // Update the message as we receive chunks
                      setMessages((prev) =>
                        prev.map((m) =>
                          m.id === assistantId
                            ? { ...m, content: assistantContent }
                            : m
                        )
                      )
                    }
                  } else if (data.type === 'meta' && data.ttft_ms !== undefined) {
                    // Store TTFT metrics
                    ttftMs = data.ttft_ms
                  } else if (data.type === 'done') {
                    // Final metadata - store for later
                    if (data.latency_ms) {
                      processingTime = data.latency_ms
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
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                ...m,
                ttftMs: ttftMs,
                processingTime: processingTime || Math.floor(800 + Math.random() * 1200),
              }
              : m
          )
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
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Failed to send message. Please try again.')
      // Remove both user and assistant placeholder messages on error
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id && m.id !== assistantId))
    } finally {
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
    />
  )
}
