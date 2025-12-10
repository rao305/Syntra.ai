'use client'

import * as React from 'react'
import { InlineMath, BlockMath } from 'react-katex'
import 'katex/dist/katex.min.css'
import { cn } from '@/lib/utils'

interface MessageContentProps {
  content: string
  className?: string
}

/**
 * MessageContent - Parses and renders message content with:
 * - Code block detection (```language blocks)
 * - LaTeX math rendering ($...$ for inline, $$...$$ for display)
 * 
 * Automatically detects and renders:
 * - Code blocks with syntax highlighting
 * - Inline math: $x^2 + y^2 = r^2$
 * - Display math: $$\int_{a}^{b} f(x) \, dx$$
 */
export function MessageContent({ content, className }: MessageContentProps) {
  // Parse content to extract code blocks and LaTeX math
  const parseContent = (
    text: string
  ): Array<{ type: 'text' | 'code' | 'math-inline' | 'math-display' | 'header' | 'paragraph'; content: string; language?: string; level?: number }> => {
    const parts: Array<{ type: 'text' | 'code' | 'math-inline' | 'math-display' | 'header' | 'paragraph'; content: string; language?: string; level?: number }> = []

    // First, extract code blocks (they take priority over LaTeX)
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g
    const codeBlockMatches: Array<{ start: number; end: number; language?: string; code: string }> = []
    let match

    while ((match = codeBlockRegex.exec(text)) !== null) {
      codeBlockMatches.push({
        start: match.index,
        end: match.index + match[0].length,
        language: match[1] || undefined,
        code: match[2].trim(),
      })
    }

    // Process text in segments, avoiding code blocks
    let lastIndex = 0

    for (const codeBlock of codeBlockMatches) {
      // Add text before code block (may contain LaTeX and markdown)
      if (codeBlock.start > lastIndex) {
        const textSegment = text.substring(lastIndex, codeBlock.start)
        parts.push(...parseMarkdownText(textSegment))
      }

      // Add code block
      if (codeBlock.code) {
        parts.push({ type: 'code', content: codeBlock.code, language: codeBlock.language })
      }

      lastIndex = codeBlock.end
    }

    // Add remaining text after last code block
    if (lastIndex < text.length) {
      const textSegment = text.substring(lastIndex)
      parts.push(...parseMarkdownText(textSegment))
    }

    // If nothing was parsed (no code blocks and no remaining text), return entire content as text
    if (parts.length === 0) {
      parts.push({ type: 'text', content: text })
    }

    return parts
  }

  // Helper: Render text with inline formatting (bold, italic, inline code)
  const renderTextWithInlineFormatting = (text: string): React.ReactNode => {
    // Parse inline formatting: **bold**, *italic*, `code`
    const parts: React.ReactNode[] = []
    let lastIndex = 0

    // Combined regex for **bold**, *italic*, and `code`
    const inlineRegex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g
    let match

    while ((match = inlineRegex.exec(text)) !== null) {
      // Add text before match
      if (match.index > lastIndex) {
        const textBefore = text.substring(lastIndex, match.index)
        parts.push(textBefore)
      }

      // Add formatted content
      if (match[2]) {
        // **bold**
        parts.push(<strong key={match.index} className="font-semibold">{match[2]}</strong>)
      } else if (match[3]) {
        // *italic*
        parts.push(<em key={match.index} className="italic">{match[3]}</em>)
      } else if (match[4]) {
        // `code`
        parts.push(
          <code
            key={match.index}
            className="px-1.5 py-0.5 rounded bg-emerald-950/30 text-emerald-300 font-mono text-[13px] border border-emerald-500/20"
          >
            {match[4]}
          </code>
        )
      }

      lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex))
    }

    return parts.length > 0 ? parts : text
  }

  // Helper: Parse markdown (headers, paragraphs) and LaTeX from text
  const parseMarkdownText = (
    text: string
  ): Array<{ type: 'text' | 'math-inline' | 'math-display' | 'header' | 'paragraph'; content: string; level?: number }> => {
    const parts: Array<{ type: 'text' | 'math-inline' | 'math-display' | 'header' | 'paragraph'; content: string; level?: number }> = []

    // Split by lines to detect headers
    const lines = text.split('\n')
    let currentParagraph: string[] = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]

      // Check for headers (### Header)
      const headerMatch = line.match(/^(#{1,6})\s+(.+)$/)

      if (headerMatch) {
        // Flush current paragraph if any
        if (currentParagraph.length > 0) {
          const paragraphText = currentParagraph.join('\n')
          parts.push(...parseMathInText(paragraphText))
          currentParagraph = []
        }

        // Add header
        const level = headerMatch[1].length
        const headerText = headerMatch[2]
        parts.push({ type: 'header', content: headerText, level })
      } else if (line.trim() === '') {
        // Empty line - flush paragraph
        if (currentParagraph.length > 0) {
          const paragraphText = currentParagraph.join('\n')
          parts.push(...parseMathInText(paragraphText))
          currentParagraph = []
        }
      } else {
        // Regular line - add to current paragraph
        currentParagraph.push(line)
      }
    }

    // Flush remaining paragraph
    if (currentParagraph.length > 0) {
      const paragraphText = currentParagraph.join('\n')
      parts.push(...parseMathInText(paragraphText))
    }

    return parts.length > 0 ? parts : [{ type: 'text', content: text }]
  }

  // Helper: Parse LaTeX math expressions from text
  const parseMathInText = (
    text: string
  ): Array<{ type: 'text' | 'math-inline' | 'math-display'; content: string }> => {
    const parts: Array<{ type: 'text' | 'math-inline' | 'math-display'; content: string }> = []

    // Match display math: $$...$$ and \[...\] (non-greedy, handles multi-line)
    const displayMathRegex = /\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\]/g
    // Match inline math: $...$ (but not $$...$$) and \(...\)
    // Simple approach: match $...$ that's not preceded or followed by another $
    const inlineMathRegex = /\$(?![$])([^$\n]+?)\$(?![$])|\\\(([\s\S]*?)\\\)/g

    const allMatches: Array<{ start: number; end: number; type: 'math-inline' | 'math-display'; content: string }> = []

    // Find all display math matches (both $$ and \[)
    let match
    while ((match = displayMathRegex.exec(text)) !== null) {
      allMatches.push({
        start: match.index,
        end: match.index + match[0].length,
        type: 'math-display',
        content: (match[1] || match[2]).trim(),
      })
    }

    // Find all inline math matches (both $ and \() - but exclude those inside display math
    displayMathRegex.lastIndex = 0 // Reset regex
    while ((match = inlineMathRegex.exec(text)) !== null) {
      // Check if this match is inside a display math block
      const isInsideDisplay = allMatches.some(
        (dm) => match.index >= dm.start && match.index < dm.end
      )

      if (!isInsideDisplay) {
        allMatches.push({
          start: match.index,
          end: match.index + match[0].length,
          type: 'math-inline',
          content: (match[1] || match[2]).trim(),
        })
      }
    }
    
    // Sort matches by position
    allMatches.sort((a, b) => a.start - b.start)
    
    // Build parts array
    let lastIndex = 0
    for (const mathMatch of allMatches) {
      // Add text before math
      if (mathMatch.start > lastIndex) {
        const textContent = text.substring(lastIndex, mathMatch.start)
        if (textContent.trim()) {
          parts.push({ type: 'text', content: textContent })
        }
      }
      
      // Add math expression
      parts.push({ type: mathMatch.type, content: mathMatch.content })
      
      lastIndex = mathMatch.end
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
      const textContent = text.substring(lastIndex)
      if (textContent.trim()) {
        parts.push({ type: 'text', content: textContent })
      }
    }
    
    // If no math found, return entire text as single part
    if (parts.length === 0) {
      parts.push({ type: 'text', content: text })
    }
    
    return parts
  }

  const parts = React.useMemo(() => parseContent(content), [content])

  // Don't render anything if content is empty
  if (!content || content.trim() === '') {
    return null
  }

  return (
    <div className={cn('space-y-4', className)}>
      {parts.map((part, index) => {
        if (part.type === 'code') {
          return (
            <pre key={index} className="bg-[#1a1a1a] rounded p-4 overflow-x-auto border border-[#2a2a2a]">
              <code className="text-sm font-mono text-white">{part.content}</code>
            </pre>
          )
        } else if (part.type === 'math-display') {
          return (
            <div key={index} className="my-4 overflow-x-auto">
              <BlockMath math={part.content} />
            </div>
          )
        } else if (part.type === 'math-inline') {
          return (
            <span key={index} className="inline-block">
              <InlineMath math={part.content} />
            </span>
          )
        } else if (part.type === 'header') {
          // Render headers with Gemini-style typography
          const HeaderTag = `h${part.level || 2}` as keyof JSX.IntrinsicElements
          const headerStyles = {
            1: 'text-[20px] font-semibold text-[#e8eaed] mb-2 mt-4',
            2: 'text-[18px] font-semibold text-[#e8eaed] mb-2 mt-3',
            3: 'text-[16px] font-semibold text-[#e8eaed] mb-1.5 mt-2',
            4: 'text-[15px] font-medium text-[#e8eaed] mb-1 mt-2',
            5: 'text-[14px] font-medium text-[#e8eaed] mb-1 mt-1',
            6: 'text-[13px] font-medium text-[#9aa0a6] mb-1 mt-1',
          }

          return (
            <HeaderTag
              key={index}
              className={headerStyles[part.level as keyof typeof headerStyles] || headerStyles[2]}
            >
              {part.content}
            </HeaderTag>
          )
        } else {
          // Regular text - render with preserved whitespace, line breaks, and inline formatting
          return (
            <div
              key={index}
              className="text-[15px] leading-[1.6] whitespace-pre-wrap break-words text-[#e8eaed]"
            >
              {renderTextWithInlineFormatting(part.content)}
            </div>
          )
        }
      })}
    </div>
  )
}
