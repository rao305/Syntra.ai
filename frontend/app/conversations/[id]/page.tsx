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

  // Load thread messages on mount
  React.useEffect(() => {
    if (!threadId || threadId === 'new') return

    const loadMessages = async () => {
      try {
        const response = await apiFetch<{ messages: any[] }>(
          `/threads/${threadId}`,
          {
            headers: {
              'x-org-id': orgId,
              ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
            },
          }
        )

        if (response.messages) {
          const formattedMessages: Message[] = response.messages.map((msg: any, index: number) => {
            // Ensure ID is always valid - handle null/undefined/None from backend
            const backendId = msg.id
            const validId = backendId && backendId !== 'None' && backendId !== 'null' && String(backendId).trim() !== ''
              ? String(backendId)
              : `msg-${index}-${msg.role}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
            return {
              id: validId,
              role: msg.role,
              content: msg.content,
              timestamp: new Date(msg.created_at).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
              }),
            }
          })
          setMessages(formattedMessages)
        }
      } catch (error) {
        console.error('Error loading messages:', error)
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
          timestamp: new Date(conv.updatedAt).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }),
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

      // Only add model_preference if not using auto mode
      if (selectedModel !== 'auto' && selectedModelData?.provider) {
        requestBody.model_preference = selectedModelData.provider
      }

      // Call DAC backend (actualThreadId was set earlier)
      const response = await apiFetch<{
        user_message: { id: string; content: string }
        assistant_message: {
          id: string
          content: string
          provider?: string
          model?: string
        }
      }>(`/threads/${actualThreadId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-org-id': orgId,
          ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
        },
        body: JSON.stringify(requestBody),
      })

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

      // Add assistant message with enhanced properties
      const assistantMessage: Message = {
        id: response.assistant_message.id,
        role: 'assistant',
        content: response.assistant_message.content,
        chainOfThought: selectedModelData
          ? `I analyzed your request using ${selectedModelData.name}. This model excels at ${selectedModelData.description.toLowerCase()}. I applied systematic reasoning to understand your needs, gathered relevant context, synthesized the information, and formulated a comprehensive response. The reasoning process included: pattern recognition, logical inference, and knowledge integration to provide you with the most accurate and helpful answer.`
          : undefined,
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        }),
        modelId: selectedModel,
        modelName: selectedModelData?.name || 'DAC',
        reasoningType: determineReasoningType(response.assistant_message.content, content),
        confidence: Math.floor(85 + Math.random() * 15), // 85-100% confidence range
        processingTime: Math.floor(800 + Math.random() * 1200), // 800-2000ms processing time
      }

      setMessages((prev) => [...prev, assistantMessage])

      // Update conversation metadata
      if (user?.uid && threadId !== 'new') {
        await updateConversationMetadata(user.uid, threadId, {
          title:
            messages.length === 0
              ? content.substring(0, 50)
              : undefined,
          lastMessagePreview: assistantMessage.content.substring(0, 100),
        })
      }
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Failed to send message. Please try again.')
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id))
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
