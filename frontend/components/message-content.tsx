'use client'

import * as React from 'react'
import { CodeBlock } from './code-block'
import { cn } from '@/lib/utils'

interface MessageContentProps {
  content: string
  className?: string
}

/**
 * MessageContent - Parses and renders message content with code block detection
 * 
 * Automatically detects code blocks (```language blocks) and renders them
 * with the enhanced CodeBlock component instead of plain text.
 */
export function MessageContent({ content, className }: MessageContentProps) {
  // Parse content to extract code blocks
  const parseContent = (text: string): Array<{ type: 'text' | 'code'; content: string; language?: string }> => {
    const parts: Array<{ type: 'text' | 'code'; content: string; language?: string }> = []
    
    // Regex to match code blocks: ```language\ncode\n``` or ```language\ncode``` (with optional newline at end)
    // Also handles code blocks without language: ```\ncode\n```
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g
    let lastIndex = 0
    let match

    while ((match = codeBlockRegex.exec(text)) !== null) {
      // Add text before code block
      if (match.index > lastIndex) {
        const textContent = text.substring(lastIndex, match.index)
        if (textContent.trim()) {
          parts.push({ type: 'text', content: textContent })
        }
      }

      // Add code block
      const language = match[1] || undefined
      const code = match[2].trim()
      if (code) {
        parts.push({ type: 'code', content: code, language })
      }

      lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < text.length) {
      const textContent = text.substring(lastIndex)
      if (textContent.trim()) {
        parts.push({ type: 'text', content: textContent })
      }
    }

    // If no code blocks found, return entire content as text
    if (parts.length === 0) {
      parts.push({ type: 'text', content: text })
    }

    return parts
  }

  const parts = React.useMemo(() => parseContent(content), [content])

  return (
    <div className={cn('space-y-3', className)}>
      {parts.map((part, index) => {
        if (part.type === 'code') {
          return (
            <CodeBlock
              key={index}
              code={part.content}
              language={part.language}
            />
          )
        } else {
          return (
            <div
              key={index}
              className="text-sm leading-relaxed whitespace-pre-wrap break-words"
            >
              {part.content}
            </div>
          )
        }
      })}
    </div>
  )
}

