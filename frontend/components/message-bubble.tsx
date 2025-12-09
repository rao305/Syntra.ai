'use client'

import { DisambiguationChips } from '@/components/disambiguation-chips'
import { MessageActions } from '@/components/message-actions'
import { MessageContent } from '@/components/message-content'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'

export interface MessageAttachment {
  type: 'image' | 'file'
  name: string
  preview?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  provider?: string
  model?: string
  reason?: string
  isLoading?: boolean
  error?: string
  ttftMs?: number // Phase 2: Time to first token in milliseconds
  cacheHit?: boolean // Phase 2: Whether this was a cache hit
  attachments?: MessageAttachment[]
  media?: Array<{
    type: 'image' | 'graph'
    url: string
    alt?: string
    mime_type?: string
  }>
  type?: 'message' | 'clarification' // Query rewriter disambiguation
  clarification?: {
    question: string
    options: string[]
    pronoun?: string
    originalMessage: string
  }
  finishReason?: string
  tokenUsage?: {
    input_tokens?: number
    output_tokens?: number
    total_tokens?: number
  }
  truncated?: boolean
}

interface MessageBubbleProps {
  message: Message
  onCopy?: (content: string) => void
  onRegenerate?: (messageId: string) => void
  onEdit?: (messageId: string) => void
  onDelete?: (messageId: string) => void
  onDisambiguationSelect?: (messageId: string, option: string, originalMessage: string) => void
  showTimestamp?: boolean
  className?: string
}

const PROVIDER_COLORS: Record<string, string> = {
  perplexity: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  openai: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  gemini: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  openrouter: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  kimi: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
}

const PROVIDER_LABELS: Record<string, string> = {
  perplexity: 'Perplexity',
  openai: 'OpenAI',
  gemini: 'Gemini',
  openrouter: 'OpenRouter',
  kimi: 'Kimi',
}

const PROVIDER_AVATARS: Record<string, string> = {
  perplexity: 'PP',
  openai: 'OA',
  gemini: 'GM',
  openrouter: 'OR',
  kimi: 'KM',
}

/**
 * MessageBubble - Enhanced message display with actions
 *
 * Features:
 * - Avatar with provider/user identification
 * - Timestamp display
 * - Provider badge with model info
 * - Hover actions (copy, regenerate, edit, delete)
 * - Error states
 * - Loading states
 * - Markdown rendering ready
 * - Gemini-style icon alignment
 */
export function MessageBubble({
  message,
  onCopy,
  onRegenerate,
  onEdit,
  onDelete,
  onDisambiguationSelect,
  showTimestamp = true,
  className,
}: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const providerKey = message.provider?.toLowerCase() || ''

  const formattedTime = format(message.timestamp, 'h:mm a')
  const formattedDate = format(message.timestamp, 'MMM d, yyyy')

  return (
    <div
      className={cn(
        'flex gap-3 group mb-8 w-full',
        isUser && 'flex-row-reverse', // User messages on the right
        className
      )}
      role="article"
      aria-label={`${message.role} message`}
      data-message-id={message.id}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? (
          <Avatar className="w-8 h-8 bg-muted">
            <AvatarFallback className="bg-[#444746] text-white text-sm font-medium">
              U
            </AvatarFallback>
          </Avatar>
        ) : (
          <div className="w-8 h-8 flex items-center justify-center rounded-full bg-emerald-500/15">
            <span className="text-xs font-semibold text-emerald-400">
              {PROVIDER_AVATARS[providerKey] || 'AI'}
            </span>
          </div>
        )}
      </div>

      {/* Message content */}
      <div className={cn('flex flex-col gap-2 flex-1', isUser ? 'items-end' : 'items-start')}>
        {/* Header: Name and timestamp */}
        {showTimestamp && (
          <div className={cn('flex items-center gap-2', isUser && 'flex-row-reverse')}>
            {!isUser && message.provider && (
              <span className="text-sm font-medium text-[#e8eaed]">
                {PROVIDER_LABELS[providerKey] || 'AI Assistant'}
              </span>
            )}
            {isUser && (
              <span className="text-sm font-medium text-[#e8eaed]">
                You
              </span>
            )}
            <time
              className="text-xs text-[#9aa0a6]"
              dateTime={message.timestamp.toISOString()}
              title={formattedDate}
            >
              {formattedTime}
            </time>
          </div>
        )}

        {/* Message content - conditional rendering based on user vs assistant */}
        {!isUser ? (
          /* AI/Assistant message */
          <div className="w-full relative">
            {/* Message actions - shown on hover */}
            <div className="absolute -top-2 right-0 opacity-0 group-hover:opacity-100 transition-opacity z-10">
              <MessageActions
                messageId={message.id}
                content={message.content}
                role={message.role}
                onCopy={onCopy}
                onRegenerate={onRegenerate}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            </div>

            {/* Message text with dark bubble */}
            <div
              className={cn(
                'relative rounded-2xl px-4 py-3 bg-[#1a1a1a] border border-[#2a2a2a]',
                message.error && 'border-destructive bg-destructive/10'
              )}
            >
              {/* Disambiguation UI */}
              {message.type === 'clarification' && message.clarification && (
                <DisambiguationChips
                  question={message.clarification.question}
                  options={message.clarification.options}
                  pronoun={message.clarification.pronoun}
                  onSelect={(option) => {
                    if (onDisambiguationSelect) {
                      onDisambiguationSelect(
                        message.id,
                        option,
                        message.clarification!.originalMessage
                      )
                    }
                  }}
                />
              )}

              {/* Generated Media (Images/Graphs) */}
              {message.media && message.media.length > 0 && (
                <div className="mb-3 space-y-3">
                  {message.media.map((mediaItem, idx) => (
                    <div key={idx} className="rounded-lg overflow-hidden border border-[#2a2a2a] bg-[#0f0f0f]">
                      {mediaItem.type === 'graph' && (
                        <div className="p-2 bg-[#1a1a1a] border-b border-[#2a2a2a]">
                          <div className="text-xs text-zinc-400 flex items-center gap-2">
                            <span>📊</span>
                            <span>Generated Graph</span>
                          </div>
                        </div>
                      )}
                      <img
                        src={mediaItem.url}
                        alt={mediaItem.alt || (mediaItem.type === 'graph' ? 'Generated graph' : 'Generated image')}
                        className="max-w-full h-auto max-h-96 object-contain w-full"
                      />
                    </div>
                  ))}
                </div>
              )}

              {/* Attachments */}
              {message.attachments && message.attachments.length > 0 && (
                <div className="mb-3 space-y-2">
                  {message.attachments.map((attachment, idx) => (
                    <div key={idx} className="rounded-lg overflow-hidden border border-[#2a2a2a]">
                      {attachment.type === 'image' && attachment.preview ? (
                        <img
                          src={attachment.preview}
                          alt={attachment.name}
                          className="max-w-full h-auto max-h-64 object-contain"
                        />
                      ) : (
                        <div className="p-4 bg-[#0f0f0f] flex items-center gap-3">
                          <div className="w-10 h-10 rounded bg-[#1a1a1a] flex items-center justify-center">
                            <span className="text-xs">📄</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate text-white">{attachment.name}</div>
                            <div className="text-xs text-gray-400">File attachment</div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Message content with white text */}
              <div className="w-full text-white text-[15px] leading-relaxed">
                <MessageContent content={message.content} />
              </div>

              {/* Error message */}
              {message.error && (
                <div className="mt-2 text-xs text-red-400">
                  ⚠️ {message.error}
                </div>
              )}
            </div>

            {/* Metadata section with green accents */}
            {(message.ttftMs !== undefined || message.provider || message.reason) && (
              <div className="flex items-center gap-2 mt-2 text-[11px]">
                {message.reason && (
                  <span className="text-emerald-400 font-medium">
                    Task: {message.reason}
                  </span>
                )}
                {message.provider && (
                  <>
                    {message.reason && <span className="text-gray-600">→</span>}
                    <span className="text-gray-400">
                      Model: {PROVIDER_LABELS[providerKey] || message.provider}
                      {message.model && ` (${message.model})`}
                    </span>
                  </>
                )}
                {message.ttftMs !== undefined && (
                  <>
                    <span className="text-gray-600">·</span>
                    <span className="text-gray-400" data-testid="ttft-badge">
                      TTFT {message.ttftMs}ms
                    </span>
                  </>
                )}
                {message.finishReason && (
                  <>
                    <span className="text-gray-600">·</span>
                    <span
                      className={cn(
                        'text-gray-400',
                        message.finishReason === 'length' && 'text-red-400 font-medium'
                      )}
                    >
                      Finish: {message.finishReason}
                    </span>
                  </>
                )}
                {message.truncated && (
                  <>
                    <span className="text-gray-600">·</span>
                    <span className="text-red-400 font-medium">
                      Output truncated
                    </span>
                  </>
                )}
              </div>
            )}
          </div>
        ) : (
          /* User message - right aligned with green bubble */
          <div className="w-full relative flex flex-col items-end">
            {/* Disambiguation UI */}
            {message.type === 'clarification' && message.clarification && (
              <DisambiguationChips
                question={message.clarification.question}
                options={message.clarification.options}
                pronoun={message.clarification.pronoun}
                onSelect={(option) => {
                  if (onDisambiguationSelect) {
                    onDisambiguationSelect(
                      message.id,
                      option,
                      message.clarification!.originalMessage
                    )
                  }
                }}
              />
            )}

            {/* Attachments */}
            {message.attachments && message.attachments.length > 0 && (
              <div className="mb-3 space-y-2 w-full">
                {message.attachments.map((attachment, idx) => (
                  <div key={idx} className="rounded-lg overflow-hidden border border-emerald-500/30">
                    {attachment.type === 'image' && attachment.preview ? (
                      <img
                        src={attachment.preview}
                        alt={attachment.name}
                        className="max-w-full h-auto max-h-64 object-contain"
                      />
                    ) : (
                      <div className="p-4 bg-emerald-950/30 flex items-center gap-3">
                        <div className="w-10 h-10 rounded bg-emerald-900/50 flex items-center justify-center">
                          <span className="text-xs">📄</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate text-white">{attachment.name}</div>
                          <div className="text-xs text-emerald-300">File attachment</div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Message content - green bubble for user messages */}
            <div className="bg-gradient-to-br from-emerald-600 to-emerald-700 text-white text-[15px] leading-relaxed rounded-2xl px-4 py-3 inline-block max-w-[80%] shadow-lg shadow-emerald-900/20">
              <MessageContent content={message.content} />
            </div>

            {/* Error message */}
            {message.error && (
              <div className="mt-2 text-xs text-red-400">
                ⚠️ {message.error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
