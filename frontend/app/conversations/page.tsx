'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { apiFetch, ApiError } from '@/lib/api'
import { ConversationLayout } from '@/components/conversation-layout'
import { ConversationList, type Conversation } from '@/components/conversation-list'
import { MessageBubble, type Message } from '@/components/message-bubble'
import { MessageComposer, type FileAttachment } from '@/components/message-composer'
import { SettingsPanel } from '@/components/settings-panel'
import { TypingIndicator } from '@/components/typing-indicator'
import { EmptyConversation } from '@/components/empty-conversation'
import { ErrorBanner } from '@/components/error-banner'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ThemeSwitcher } from '@/components/theme-switcher'
import { Button } from '@/components/ui/button'
import { Settings, MessageSquare } from 'lucide-react'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

type Provider = 'perplexity' | 'openai' | 'gemini' | 'openrouter' | 'kimi'

interface RouterResponse {
  provider: Provider
  model: string
  reason: string
}

interface SendMessageResponse {
  user_message: {
    id: string
    content: string
    role: string
    created_at: string
  }
  assistant_message: {
    id: string
    content: string
    role: string
    created_at: string
    provider?: string
    model?: string
  }
}

const ORG_ID = 'org_demo' // Dev mode

// Mock available models (in production, fetch from API)
const AVAILABLE_MODELS = [
  { id: 'gpt-4', name: 'GPT-4', provider: 'openai', description: 'Most capable model' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai', description: 'Fast and efficient' },
  { id: 'sonar-pro', name: 'Sonar Pro', provider: 'perplexity', description: 'Web-grounded reasoning' },
  { id: 'sonar-reasoning', name: 'Sonar Reasoning', provider: 'perplexity', description: 'Deep analysis with sources' },
  { id: 'gemini-pro', name: 'Gemini Pro', provider: 'gemini', description: 'Multimodal AI' },
]

export default function ConversationsPage() {
  const router = useRouter()

  // State
  const [conversations, setConversations] = React.useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = React.useState<string | null>(null)
  const [messages, setMessages] = React.useState<Message[]>([])
  const [inputValue, setInputValue] = React.useState('')
  const [attachments, setAttachments] = React.useState<FileAttachment[]>([])
  const [isLoading, setIsLoading] = React.useState(false)
  const [isSending, setIsSending] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [showSettings, setShowSettings] = React.useState(false)
  const abortControllerRef = React.useRef<AbortController | null>(null)
  const [cancelled, setCancelled] = React.useState(false)

  // Settings state (unused - router decides automatically)
  const [selectedModels, setSelectedModels] = React.useState<string[]>([])
  const [systemPrompt, setSystemPrompt] = React.useState('')
  const [temperature, setTemperature] = React.useState(0.7)
  const [maxTokens, setMaxTokens] = React.useState(2000)

  // Typing indicator state
  const [currentProvider, setCurrentProvider] = React.useState<Provider | undefined>()
  const [currentModel, setCurrentModel] = React.useState<string | undefined>()
  const [currentReason, setCurrentReason] = React.useState<string | undefined>()

  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const scrollAreaRef = React.useRef<HTMLDivElement>(null)
  const isUserScrollingRef = React.useRef(false)
  const scrollTimeoutRef = React.useRef<NodeJS.Timeout | null>(null)

  // Check if user is near the bottom of the scroll area
  const isNearBottom = (): boolean => {
    if (!scrollAreaRef.current) return true // Default to true if ref not set
    
    const viewport = scrollAreaRef.current.querySelector('[data-slot="scroll-area-viewport"]') as HTMLElement
    if (!viewport) return true // Default to true if we can't find viewport
    
    const threshold = 150 // pixels from bottom
    const scrollTop = viewport.scrollTop
    const scrollHeight = viewport.scrollHeight
    const clientHeight = viewport.clientHeight
    
    return scrollHeight - scrollTop - clientHeight < threshold
  }

  // Scroll to bottom of messages (only if user is near bottom)
  const scrollToBottom = (force = false) => {
    // If user has scrolled up, don't auto-scroll unless forced
    if (!force && !isNearBottom()) {
      return
    }
    
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Handle scroll events to detect user scrolling
  const handleScroll = React.useCallback(() => {
    isUserScrollingRef.current = true
    
    // Clear existing timeout
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current)
    }
    
    // Reset flag after user stops scrolling
    scrollTimeoutRef.current = setTimeout(() => {
      isUserScrollingRef.current = false
    }, 150)
  }, [])

  // Attach scroll listener
  React.useEffect(() => {
    if (!scrollAreaRef.current) return
    
    const viewport = scrollAreaRef.current.querySelector('[data-slot="scroll-area-viewport"]') as HTMLElement
    if (viewport) {
      viewport.addEventListener('scroll', handleScroll, { passive: true })
      return () => {
        viewport.removeEventListener('scroll', handleScroll)
        if (scrollTimeoutRef.current) {
          clearTimeout(scrollTimeoutRef.current)
        }
      }
    }
  }, [handleScroll])

  // Auto-scroll only if user is near bottom (hasn't scrolled up)
  React.useEffect(() => {
    // Small delay to ensure DOM is updated
    const timeoutId = setTimeout(() => {
      // Only auto-scroll if user is near the bottom (hasn't manually scrolled up)
      // Don't scroll if user is actively scrolling
      if (isNearBottom() && !isUserScrollingRef.current) {
        scrollToBottom()
      }
    }, 100)
    
    return () => clearTimeout(timeoutId)
  }, [messages, isSending])

  // Load conversations on mount
  React.useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    setIsLoading(true)
    try {
      // Note: Backend doesn't have GET /threads/ endpoint yet
      // For now, just set empty conversations - Phase 3 will add this
      // This prevents the page from crashing when the API call fails
      setConversations([])
    } catch (err) {
      console.error('Failed to load conversations:', err)
      // Silently fail - page should still render
      setConversations([])
    } finally {
      setIsLoading(false)
    }
  }

  const createNewConversation = async () => {
    setActiveConversationId(null)
    setMessages([])
    setError(null)
    setInputValue('')
  }

  const handleConversationSelect = (id: string) => {
    setActiveConversationId(id)
    setMessages([]) // In production, load messages for this conversation
    setError(null)
  }

  const handleSendMessage = async () => {
    const trimmed = inputValue.trim()
    if ((!trimmed && attachments.length === 0) || isSending) return

    setError(null)
    setIsSending(true)
    
    // Convert attachments to base64
    const attachmentData = await Promise.all(
      attachments.map(async (attachment) => {
        const base64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            const result = reader.result as string
            // Remove data URL prefix (e.g., "data:image/png;base64,")
            const base64Data = result.split(',')[1]
            resolve(base64Data)
          }
          reader.onerror = reject
          reader.readAsDataURL(attachment.file)
        })

        return {
          type: attachment.type,
          name: attachment.file.name,
          mimeType: attachment.file.type,
          data: base64,
        }
      })
    )

    const optimisticId = `msg_${Date.now()}`
    const optimisticMessage: Message = {
      id: optimisticId,
      role: 'user',
      content: trimmed || (attachments.length > 0 ? `[${attachments.length} file(s) attached]` : ''),
      timestamp: new Date(),
      attachments: attachments.map((a) => ({
        type: a.type,
        name: a.file.name,
        preview: a.preview,
      })),
    }

    setMessages((prev) => [...prev, optimisticMessage])
    setInputValue('')
    setAttachments([])
    // Force scroll to bottom when user sends a message
    setTimeout(() => scrollToBottom(true), 50)

    // Create streaming message placeholder
    const streamingMsgId = `streaming_${Date.now()}`
    const streamingMessage: Message = {
      id: streamingMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      provider: currentProvider,
      model: currentModel,
      reason: currentReason,
    }
    setMessages((prev) => [...prev, streamingMessage])

    // Create AbortController for cancel functionality
    abortControllerRef.current = new AbortController()
    setCancelled(false)

    try {
      // Use the /api/chat endpoint which handles streaming
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-org-id': ORG_ID,
        },
        body: JSON.stringify({
          messages: [{ role: 'user', content: trimmed || '' }],
          attachments: attachmentData.length > 0 ? attachmentData : undefined,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let assistantContent = ''
      let ttftMs: number | undefined
      let cacheHit = false
      const streamStartTime = performance.now()
      let firstTokenReceived = false

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        let frameEnd
        while ((frameEnd = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, frameEnd)
          buffer = buffer.slice(frameEnd + 2)

          let eventType = 'delta'
          let dataLine = ''
          for (const line of frame.split('\n')) {
            if (line.startsWith('event:')) eventType = line.slice(6).trim()
            if (line.startsWith('data:')) dataLine += line.slice(5).trim()
          }

          if (!dataLine) continue

          try {
            const data = JSON.parse(dataLine)

            // Handle router event (provider/model selection)
            if (eventType === 'router') {
              if (data.provider) setCurrentProvider(data.provider as Provider)
              if (data.model) setCurrentModel(data.model)
              if (data.reason) setCurrentReason(data.reason)
              
              // Update the streaming message with router info
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamingMsgId
                    ? {
                        ...msg,
                        provider: data.provider,
                        model: data.model,
                        reason: data.reason,
                      }
                    : msg
                )
              )
            }

            // Handle meta events (TTFT, cache hit)
            if (eventType === 'meta') {
              if (data.ttft_ms !== undefined) {
                ttftMs = data.ttft_ms
              }
              if (data.cache_hit !== undefined) {
                cacheHit = data.cache_hit
              }
            }

            // Handle delta events
            if (eventType === 'delta' && data.delta) {
              // Track TTFT from first token if not already set
              if (!firstTokenReceived && ttftMs === undefined) {
                ttftMs = Math.round(performance.now() - streamStartTime)
                firstTokenReceived = true
              }
              assistantContent += data.delta
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamingMsgId
                    ? {
                        ...msg,
                        content: assistantContent,
                        ttftMs,
                        cacheHit,
                      }
                    : msg
                )
              )
            }

            // Handle done event
            if (eventType === 'done') {
              // Finalize message
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamingMsgId
                    ? {
                        ...msg,
                        content: assistantContent,
                        ttftMs,
                        cacheHit,
                      }
                    : msg
                )
              )
              break
            }

            // Handle error event
            if (eventType === 'error') {
              const errorMsg = data.error || 'Stream error'
              setError(`Provider error: ${errorMsg}`)
              setMessages((prev) => prev.filter((msg) => msg.id !== streamingMsgId))
              break
            }
          } catch (e) {
            // Ignore parse errors for non-JSON data
          }
        }
      }
    } catch (err: any) {
      // Handle cancellation
      if (err?.name === 'AbortError' || abortControllerRef.current?.signal.aborted) {
        setCancelled(true)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === streamingMsgId
              ? { ...msg, content: msg.content || 'cancelled', error: 'cancelled' }
              : msg
          )
        )
        return
      }

      if (err instanceof ApiError) {
        if (err.status === 429) {
          setError('Rate limit exceeded. Please try again later.')
        } else {
          setError(err.message)
        }
      } else {
        setError('Failed to send message. Please try again.')
      }
      setMessages((prev) => prev.filter((msg) => msg.id !== optimisticId && msg.id !== streamingMsgId))
    } finally {
      setIsSending(false)
      abortControllerRef.current = null
    }
  }

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setCancelled(true)
      setIsSending(false)
    }
  }

  const handlePromptSelect = (prompt: string) => {
    setInputValue(prompt)
  }

  const handleCopyMessage = (content: string) => {
    toast.success('Copied to clipboard')
  }

  const handleRegenerateMessage = (messageId: string) => {
    toast.info('Regenerating response...')
    // TODO: Implement regeneration
  }

  const handleEditMessage = (messageId: string) => {
    toast.info('Edit functionality coming soon')
    // TODO: Implement editing
  }

  const handleDeleteMessage = (messageId: string) => {
    setMessages((prev) => prev.filter((msg) => msg.id !== messageId))
    toast.success('Message deleted')
  }

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: 'n',
      metaKey: true,
      callback: createNewConversation,
      description: 'New conversation',
    },
    {
      key: ',',
      metaKey: true,
      callback: () => setShowSettings((prev) => !prev),
      description: 'Toggle settings',
    },
  ])

  return (
    <ConversationLayout
      showRightPanel={showSettings}
      leftSidebar={
        <ConversationList
          conversations={conversations}
          activeConversationId={activeConversationId || undefined}
          onConversationSelect={handleConversationSelect}
          onNewConversation={createNewConversation}
          isLoading={isLoading}
        />
      }
      rightPanel={
        <SettingsPanel
          selectedModels={selectedModels}
          availableModels={AVAILABLE_MODELS}
          onModelChange={setSelectedModels}
          systemPrompt={systemPrompt}
          onSystemPromptChange={setSystemPrompt}
          temperature={temperature}
          onTemperatureChange={setTemperature}
          maxTokens={maxTokens}
          onMaxTokensChange={setMaxTokens}
          onClose={() => setShowSettings(false)}
        />
      }
    >
      {/* Main conversation view */}
      <div className="h-full flex flex-col overflow-hidden">
        {/* Header - Compact when no messages */}
        <div className={cn(
          "border-b border-border px-6 flex items-center justify-between bg-zinc-900/60 backdrop-blur-xl supports-[backdrop-filter]:bg-zinc-900/40 flex-shrink-0",
          messages.length === 0 && !isSending ? "py-2.5" : "py-4"
        )}>
          <div className="flex items-center gap-3">
            <MessageSquare className="w-5 h-5 text-emerald-400" />
            <div>
              <h1 className="text-base font-semibold text-foreground">
                {activeConversationId
                  ? conversations.find((c) => c.id === activeConversationId)?.title ||
                    'DAC — Multi-LLM Assistant for Teams'
                  : 'DAC — Multi-LLM Assistant for Teams'}
              </h1>
              {messages.length === 0 && !isSending && (
                <div className="flex items-center gap-2.5 mt-0.5">
                  <span className="text-[10px] text-emerald-400/70">4+ Providers</span>
                  <span className="text-[10px] text-muted-foreground/50">•</span>
                  <span className="text-[10px] text-blue-400/70">Smart Routing</span>
                  <span className="text-[10px] text-muted-foreground/50">•</span>
                  <span className="text-[10px] text-purple-400/70">Secure by Design</span>
                </div>
              )}
              {selectedModels.length > 0 && messages.length > 0 && (
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-muted-foreground">•</span>
                  <span className="text-[10px] text-emerald-400">Using: {selectedModels.join(', ')}</span>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeSwitcher />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSettings((prev) => !prev)}
              className={showSettings ? 'bg-accent' : ''}
            >
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="p-4">
            <ErrorBanner
              type={error.includes('Rate limit') ? 'ratelimit' : 'api'}
              message={error}
              onRetry={() => setError(null)}
              onDismiss={() => setError(null)}
            />
          </div>
        )}

        {/* Messages area - Gemini-inspired cascading layout */}
        <div ref={scrollAreaRef} className="flex-1 relative overflow-hidden min-h-0">
          {messages.length === 0 && !isSending ? (
            // Centered empty state - no scroll area needed
            <div className="h-full flex items-center justify-center p-6">
              <div className="w-full max-w-3xl mx-auto">
                <EmptyConversation onPromptSelect={handlePromptSelect} />
              </div>
            </div>
          ) : (
            // Conversation view with scroll
            <ScrollArea className="h-full">
              <div 
                className="p-6 space-y-6 transition-all duration-500 ease-out"
                role="log" 
                aria-live="polite" 
                aria-label="Conversation messages"
              >
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    onCopy={handleCopyMessage}
                    onRegenerate={handleRegenerateMessage}
                    onEdit={handleEditMessage}
                    onDelete={handleDeleteMessage}
                    showTimestamp
                  />
                ))}
                {cancelled && (
                  <div className="text-sm text-muted-foreground italic px-4 py-2" data-testid="cancelled-indicator">
                    cancelled
                  </div>
                )}

                {isSending && (
                  <TypingIndicator provider={currentProvider} model={currentModel} reason={currentReason} />
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>
          )}
        </div>

        {/* Message composer - Gemini-inspired compact design */}
        <div className={cn(
          "border-t border-border/50 bg-background/95 backdrop-blur-sm",
          "transition-all duration-300",
          messages.length === 0 && !isSending 
            ? "px-6 py-4 flex items-center justify-center" 
            : "px-6 py-4"
        )}>
          <div className={cn(
            "w-full transition-all duration-300",
            messages.length === 0 && !isSending ? "max-w-2xl" : "max-w-full"
          )}>
            <MessageComposer
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSendMessage}
              onCancel={isSending ? handleCancel : undefined}
              isLoading={isSending}
              selectedModels={selectedModels}
              showCharacterCount={messages.length > 0 || isSending}
              autoFocus
              attachments={attachments}
              onAttachmentsChange={setAttachments}
              className={messages.length === 0 && !isSending ? "max-w-2xl mx-auto" : ""}
            />
          </div>
        </div>
      </div>
    </ConversationLayout>
  )
}
