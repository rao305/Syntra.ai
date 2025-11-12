'use client'

import * as React from 'react'
import { format } from 'date-fns'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { MessageActions } from '@/components/message-actions'
import { MessageContent } from '@/components/message-content'
import { cn } from '@/lib/utils'

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
}

interface MessageBubbleProps {
  message: Message
  onCopy?: (content: string) => void
  onRegenerate?: (messageId: string) => void
  onEdit?: (messageId: string) => void
  onDelete?: (messageId: string) => void
  showTimestamp?: boolean
  className?: string
}

const PROVIDER_COLORS: Record<string, string> = {
  perplexity: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  openai: 'bg-green-500/20 text-green-300 border-green-500/30',
  gemini: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  openrouter: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  kimi: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
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
 */
export function MessageBubble({
  message,
  onCopy,
  onRegenerate,
  onEdit,
  onDelete,
  showTimestamp = true,
  className,
}: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  const providerKey = message.provider?.toLowerCase() || ''

  const formattedTime = format(message.timestamp, 'h:mm a')
  const formattedDate = format(message.timestamp, 'MMM d, yyyy')

  return (
    <div
      className={cn(
        'flex gap-3 group',
        isUser ? 'justify-end' : 'justify-start',
        className
      )}
      role="article"
      aria-label={`${message.role} message`}
    >
      {/* Avatar - Left side for assistant, right side for user */}
      {!isUser && (
        <Avatar className={cn(
          'w-8 h-8 flex-shrink-0 ring-2',
          message.provider && PROVIDER_COLORS[providerKey]
            ? 'ring-accent/30'
            : 'ring-accent/30'
        )}>
          <AvatarFallback className={cn(
            'text-xs font-bold',
            message.provider && PROVIDER_COLORS[providerKey]
              ? PROVIDER_COLORS[providerKey]
              : 'bg-accent/20 text-accent'
          )}>
            {message.provider ? PROVIDER_AVATARS[providerKey] || 'AI' : 'AI'}
          </AvatarFallback>
        </Avatar>
      )}

      {/* Message content */}
      <div className={cn('flex flex-col gap-1.5', isUser ? 'items-end' : 'items-start')}>
        {/* Header: Name and timestamp */}
        <div className="flex items-center gap-2 px-1">
          {!isUser && (
            <span className="text-xs font-medium text-foreground">
              {message.provider ? PROVIDER_LABELS[providerKey] || 'AI Assistant' : 'AI Assistant'}
            </span>
          )}
          {showTimestamp && (
            <time
              className="text-[10px] text-muted-foreground"
              dateTime={message.timestamp.toISOString()}
              title={formattedDate}
            >
              {formattedTime}
            </time>
          )}
        </div>

        {/* Message bubble with content */}
        <div
          className={cn(
            'relative max-w-sm lg:max-w-md xl:max-w-lg rounded-lg transition-all',
            isUser
              ? 'bg-accent text-accent-foreground rounded-br-none'
              : 'bg-card border border-border text-card-foreground rounded-bl-none',
            message.error && 'border-destructive bg-destructive/10'
          )}
        >
          {/* Message actions - shown on hover */}
          <div className="absolute -top-8 right-0 opacity-0 group-hover:opacity-100 transition-opacity">
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

          {/* Content */}
          <div className="p-4">
            {/* Attachments */}
            {message.attachments && message.attachments.length > 0 && (
              <div className="mb-3 space-y-2">
                {message.attachments.map((attachment, idx) => (
                  <div key={idx} className="rounded-lg overflow-hidden border border-border/50">
                    {attachment.type === 'image' && attachment.preview ? (
                      <img
                        src={attachment.preview}
                        alt={attachment.name}
                        className="max-w-full h-auto max-h-64 object-contain"
                      />
                    ) : (
                      <div className="p-4 bg-muted/50 flex items-center gap-3">
                        <div className="w-10 h-10 rounded bg-background flex items-center justify-center">
                          <span className="text-xs">📄</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{attachment.name}</div>
                          <div className="text-xs text-muted-foreground">File attachment</div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            <MessageContent content={message.content} />

            {/* Error message */}
            {message.error && (
              <div className="mt-2 text-xs text-destructive-foreground">
                ⚠️ {message.error}
              </div>
            )}

            {/* Phase 2: Performance badges (TTFT, cache hit) */}
            {isAssistant && (message.ttftMs !== undefined || message.cacheHit) && (
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                {message.cacheHit && (
                  <Badge variant="secondary" className="text-[10px] px-2 py-0.5" data-testid="cache-hit-badge">
                    cache_hit
                  </Badge>
                )}
                {message.ttftMs !== undefined && (
                  <Badge variant="outline" className="text-[10px] px-2 py-0.5" data-testid="ttft-badge">
                    TTFT {message.ttftMs}ms
                  </Badge>
                )}
              </div>
            )}

            {/* Provider info and routing reason */}
            {isAssistant && message.provider && (
              <div className="mt-3 flex items-center gap-2 flex-wrap">
                <Badge
                  variant="outline"
                  className={cn(
                    'text-[10px] px-2 py-0.5',
                    PROVIDER_COLORS[providerKey] || 'bg-gray-500/20 text-gray-300'
                  )}
                >
                  {PROVIDER_LABELS[providerKey] || message.provider}
                  {message.model && (
                    <span className="ml-1 opacity-70">· {message.model}</span>
                  )}
                </Badge>

                {message.reason && (
                  <span className="text-[10px] text-muted-foreground">
                    {message.reason}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* User avatar */}
      {isUser && (
        <Avatar className="w-8 h-8 flex-shrink-0 ring-2 ring-primary/30">
          <AvatarFallback className="bg-primary text-primary-foreground text-xs font-bold">
            U
          </AvatarFallback>
        </Avatar>
      )}
    </div>
  )
}
