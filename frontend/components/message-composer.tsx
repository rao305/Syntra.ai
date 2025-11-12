'use client'

import * as React from 'react'
import { Send, Sparkles, Loader2, Paperclip, X, Image as ImageIcon, File } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface FileAttachment {
  id: string
  file: File
  preview?: string // For images
  type: 'image' | 'file'
}

interface MessageComposerProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onCancel?: () => void
  isLoading?: boolean
  disabled?: boolean
  selectedModels?: string[]
  onModelToggle?: (model: string) => void
  placeholder?: string
  maxLength?: number
  showCharacterCount?: boolean
  autoFocus?: boolean
  className?: string
  attachments?: FileAttachment[]
  onAttachmentsChange?: (attachments: FileAttachment[]) => void
}

/**
 * MessageComposer - Enhanced multiline input for composing messages
 *
 * Features:
 * - Auto-resizing textarea
 * - Character count
 * - Model selection badges
 * - Keyboard shortcuts (Cmd/Ctrl+Enter to send, Esc to cancel)
 * - Loading state
 * - Disabled state
 * - Submit validation
 */
export function MessageComposer({
  value,
  onChange,
  onSubmit,
  onCancel,
  isLoading = false,
  disabled = false,
  selectedModels = [],
  onModelToggle,
  placeholder = 'Type your message...',
  maxLength = 10000,
  showCharacterCount = true,
  autoFocus = false,
  className,
  attachments = [],
  onAttachmentsChange,
}: MessageComposerProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const [isFocused, setIsFocused] = React.useState(false)
  const [isDragging, setIsDragging] = React.useState(false)
  const [internalAttachments, setInternalAttachments] = React.useState<FileAttachment[]>(attachments || [])

  // Sync internal attachments with prop
  React.useEffect(() => {
    if (attachments) {
      setInternalAttachments(attachments)
    }
  }, [attachments])

  const characterCount = value.length
  const isNearLimit = characterCount > maxLength * 0.9
  const isOverLimit = characterCount > maxLength
  const canSubmit = (value.trim().length > 0 || internalAttachments.length > 0) && !isLoading && !disabled && !isOverLimit

  // Handle file processing
  const processFiles = React.useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files)
    const newAttachments: FileAttachment[] = []

    fileArray.forEach((file) => {
      const id = `${Date.now()}-${Math.random()}`
      const isImage = file.type.startsWith('image/')
      
      const attachment: FileAttachment = {
        id,
        file,
        type: isImage ? 'image' : 'file',
      }

      // Create preview for images
      if (isImage) {
        const reader = new FileReader()
        reader.onload = (e) => {
          attachment.preview = e.target?.result as string
          setInternalAttachments((prev) => {
            const updated = [...prev]
            const index = updated.findIndex((a) => a.id === id)
            if (index >= 0) {
              updated[index] = { ...updated[index], preview: attachment.preview }
            }
            return updated
          })
          if (onAttachmentsChange) {
            const current = [...internalAttachments, ...newAttachments]
            const index = current.findIndex((a) => a.id === id)
            if (index >= 0) {
              current[index] = { ...current[index], preview: attachment.preview }
            }
            onAttachmentsChange(current)
          }
        }
        reader.readAsDataURL(file)
      }

      newAttachments.push(attachment)
    })

    const updated = [...internalAttachments, ...newAttachments]
    setInternalAttachments(updated)
    if (onAttachmentsChange) {
      onAttachmentsChange(updated)
    }
  }, [internalAttachments, onAttachmentsChange])

  // Handle file input change
  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      processFiles(e.target.files)
      e.target.value = '' // Reset input
    }
  }

  // Handle drag and drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled && !isLoading) {
      setIsDragging(true)
    }
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    if (disabled || isLoading) return

    const files = e.dataTransfer.files
    if (files.length > 0) {
      processFiles(files)
    }
  }

  // Remove attachment
  const removeAttachment = (id: string) => {
    const updated = internalAttachments.filter((a) => a.id !== id)
    setInternalAttachments(updated)
    if (onAttachmentsChange) {
      onAttachmentsChange(updated)
    }
  }

  // Auto-resize textarea
  React.useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    textarea.style.height = `${textarea.scrollHeight}px`
  }, [value])

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter to send
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      if (canSubmit) {
        onSubmit()
      }
    }

    // Escape to cancel
    if (e.key === 'Escape' && onCancel) {
      e.preventDefault()
      onCancel()
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (canSubmit) {
      onSubmit()
    }
  }

  // Check if in compact mode (centered initial state)
  const isCompactMode = className?.includes('max-w-3xl')
  
  return (
    <form
      onSubmit={handleSubmit}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        'transition-all',
        isCompactMode 
          ? 'bg-transparent border-0' 
          : 'border-t border-border/50 bg-background/95 backdrop-blur-sm',
        isFocused && !isCompactMode && 'border-accent/30',
        isDragging && 'border-emerald-500/50 bg-emerald-500/5',
        className
      )}
    >
      <div className={cn('space-y-2', isCompactMode ? 'p-0' : 'p-3')}>
        {/* File attachments preview */}
        {internalAttachments.length > 0 && (
          <div className="flex flex-wrap gap-2 p-2 bg-muted/30 rounded-lg">
            {internalAttachments.map((attachment) => (
              <div
                key={attachment.id}
                className="relative group flex items-center gap-2 p-2 bg-background rounded border border-border"
              >
                {attachment.type === 'image' && attachment.preview ? (
                  <img
                    src={attachment.preview}
                    alt={attachment.file.name}
                    className="w-16 h-16 object-cover rounded"
                  />
                ) : (
                  <div className="w-16 h-16 flex items-center justify-center bg-muted rounded">
                    <File className="w-6 h-6 text-muted-foreground" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-foreground truncate">
                    {attachment.file.name}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {(attachment.file.size / 1024).toFixed(1)} KB
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={() => removeAttachment(attachment.id)}
                  aria-label="Remove attachment"
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
            ))}
          </div>
        )}

        {/* Drag overlay hint */}
        {isDragging && (
          <div className="absolute inset-0 flex items-center justify-center bg-emerald-500/10 border-2 border-dashed border-emerald-500/50 rounded-lg z-10 pointer-events-none">
            <div className="text-center space-y-2">
              <ImageIcon className="w-12 h-12 mx-auto text-emerald-400" />
              <p className="text-sm font-medium text-emerald-400">Drop files here</p>
            </div>
          </div>
        )}
        {/* Selected models */}
        {selectedModels.length > 0 && onModelToggle && (
          <div className="flex items-center gap-2 flex-wrap">
            <Sparkles className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Using:</span>
            {selectedModels.map((model) => (
              <Badge
                key={model}
                variant="secondary"
                className="text-xs cursor-pointer hover:bg-secondary/80"
                onClick={() => onModelToggle(model)}
              >
                {model}
                <span className="ml-1.5 text-muted-foreground hover:text-foreground">×</span>
              </Badge>
            ))}
          </div>
        )}

        {/* Textarea - Gemini-inspired compact design */}
        <div className={cn(
          'relative rounded-2xl border border-border/60 bg-background/50 backdrop-blur-sm transition-all',
          isCompactMode ? 'px-4 py-3' : 'px-4 py-3',
          isFocused && 'ring-1 ring-accent/30 border-accent/50 bg-background shadow-sm',
          isDragging && 'border-emerald-500/50 bg-emerald-500/5',
          disabled && 'opacity-50 cursor-not-allowed'
        )}>
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={isCompactMode ? "Ask DAC" : placeholder}
            disabled={disabled || isLoading}
            autoFocus={autoFocus}
            className={cn(
              'min-h-[44px] max-h-[200px] resize-none border-0 bg-transparent',
              'text-sm leading-relaxed placeholder:text-muted-foreground/70',
              'focus-visible:ring-0 focus-visible:ring-offset-0',
              'px-0 py-0',
              isCompactMode && 'text-base',
              isOverLimit && 'text-destructive'
            )}
            aria-label="Message input"
            aria-describedby="character-count keyboard-hint"
          />

          {/* Action buttons inside input (Gemini-style) */}
          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            {!isLoading && canSubmit && (
              <Button
                type="submit"
                size="sm"
                className="h-7 px-3 text-xs bg-emerald-500 hover:bg-emerald-600 text-white"
                aria-label="Send message"
              >
                <Send className="w-3.5 h-3.5" />
              </Button>
            )}
            {isLoading && onCancel && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={onCancel}
                className="h-7 px-3 text-xs"
                aria-label="Cancel"
              >
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              </Button>
            )}
          </div>
        </div>

        {/* Footer - Compact mode shows disclaimer, normal mode shows hints */}
        {isCompactMode ? (
          <div className="text-[10px] text-muted-foreground/50 text-center px-1">
            DAC can make mistakes, so double-check important information
          </div>
        ) : (
          <div className="flex items-center justify-between text-xs text-muted-foreground/60 px-1">
            <span id="keyboard-hint" className="hidden sm:block">
              <kbd className="px-1.5 py-0.5 bg-muted/50 rounded text-[10px]">
                {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}
              </kbd>
              <span className="mx-1">+</span>
              <kbd className="px-1.5 py-0.5 bg-muted/50 rounded text-[10px]">Enter</kbd>
              <span className="ml-1">to send</span>
            </span>
            {showCharacterCount && (
              <span
                id="character-count"
                className={cn(
                  'tabular-nums text-[10px]',
                  isNearLimit && 'text-yellow-500',
                  isOverLimit && 'text-destructive font-medium'
                )}
                aria-live="polite"
              >
                {characterCount.toLocaleString()} / {maxLength.toLocaleString()}
              </span>
            )}
          </div>
        )}

        {/* File attachment button - only show in normal mode */}
        {!isCompactMode && (
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,.pdf,.txt,.doc,.docx,.csv,.json"
              onChange={handleFileInput}
              className="hidden"
              aria-label="Upload file"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || isLoading}
              aria-label="Attach file"
              title="Attach file or image"
            >
              <Paperclip className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>
    </form>
  )
}
