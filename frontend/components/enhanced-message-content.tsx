'use client'

import { ImageMessageDisplay } from '@/components/image-message-display'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import 'katex/dist/katex.min.css'
import { Check, Copy, Maximize2 } from 'lucide-react'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { BlockMath, InlineMath } from 'react-katex'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import remarkGfm from 'remark-gfm'

interface CodeBlockProps {
  children: React.ReactNode
  className?: string
}

interface ImageFile {
  file?: File
  url: string
  id: string
}

interface EnhancedMessageContentProps {
  content: string
  role: 'user' | 'assistant'
  images?: ImageFile[]
  onCodePanelOpen?: (code: string, language: string) => void
}

// Threshold for determining when to show code in parallel panel (characters)
const LARGE_CODE_THRESHOLD = 300

// Persistent state for code block expansion across re-renders
// Key: hash of code content, Value: expanded state
const codeBlockExpandedState = new Map<string, boolean>()

// Simple hash function for code content
function hashCode(str: string): string {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32bit integer
  }
  return String(Math.abs(hash))
}

// Custom code block component
const CodeBlock: React.FC<CodeBlockProps> = ({ children, className }) => {
  const [copied, setCopied] = useState(false)

  const language = className?.replace('language-', '') || 'text'
  const codeString = String(children).replace(/\n$/, '')
  const codeHash = hashCode(codeString)

  // Use persistent state from Map - always read current value
  const persistedExpanded = codeBlockExpandedState.get(codeHash) || false
  const [isExpanded, setIsExpanded] = useState(persistedExpanded)
  const initializedRef = useRef(false)

  // Initialize and sync state from persistent storage
  useEffect(() => {
    const currentPersisted = codeBlockExpandedState.get(codeHash) || false
    setIsExpanded(currentPersisted)
    initializedRef.current = true
  }, [codeHash])

  // Update persistent state when expanded state changes
  const handleSetExpanded = useCallback((expanded: boolean) => {
    console.log('Expanding code block:', {
      codeHash,
      expanded,
      codeLength: codeString.length,
      lines: codeString.split('\n').length,
      currentState: isExpanded,
      persistedState: codeBlockExpandedState.get(codeHash)
    })
    // Update Map first, then state - use functional update to ensure we get latest
    codeBlockExpandedState.set(codeHash, expanded)
    setIsExpanded(expanded)
  }, [codeHash, codeString.length, isExpanded])

  const isLargeCode = codeString.length > LARGE_CODE_THRESHOLD

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(codeString)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy code:', err)
    }
  }

  const handleExpand = () => {
    if (window.onCodePanelOpen) {
      window.onCodePanelOpen(codeString, language)
    }
  }

  // Small code snippets - inline with background
  if (!isLargeCode) {
    return (
      <div className="relative rounded-lg overflow-hidden border border-zinc-700/50 bg-zinc-900/80 my-3">
        <div className="flex items-center justify-between px-3 py-2 bg-zinc-800/50 border-b border-zinc-700/30">
          <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
            {language}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-6 px-2 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50 transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 mr-1" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 mr-1" />
                  Copy
                </>
              )}
            </Button>
          </div>
        </div>
        <div className="p-3 overflow-x-auto">
          <SyntaxHighlighter
            style={vscDarkPlus}
            language={language}
            customStyle={{
              margin: 0,
              padding: 0,
              background: 'transparent',
              fontSize: '13px',
              lineHeight: '1.5'
            }}
          >
            {codeString}
          </SyntaxHighlighter>
        </div>
      </div>
    )
  }

  // Large code blocks - show preview with expand option
  const previewLines = codeString.split('\n').slice(0, 8).join('\n')
  const hasMoreLines = codeString.split('\n').length > 8

  return (
    <div className="relative rounded-lg overflow-hidden border border-zinc-700/50 bg-zinc-900/80 my-3">
      <div className="flex items-center justify-between px-3 py-2 bg-zinc-800/50 border-b border-zinc-700/30">
        <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
          {language} • {codeString.split('\n').length} lines
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              console.log('Expand All clicked')
              handleSetExpanded(true)
            }}
            className="h-6 px-2 text-xs text-blue-400 hover:text-blue-300 hover:bg-blue-900/20 transition-colors cursor-pointer"
          >
            <Maximize2 className="w-3 h-3 mr-1" />
            Expand All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-6 px-2 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 mr-1" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 mr-1" />
                Copy
              </>
            )}
          </Button>
        </div>
      </div>
      <div className="p-3 overflow-x-auto">
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={language}
          customStyle={{
            margin: 0,
            padding: 0,
            background: 'transparent',
            fontSize: '13px',
            lineHeight: '1.5'
          }}
        >
          {isExpanded ? codeString : previewLines}
        </SyntaxHighlighter>
        {hasMoreLines && !isExpanded && (
          <div className="mt-2 pt-2 border-t border-zinc-700/30">
            <button
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                console.log('Show more lines clicked')
                handleSetExpanded(true)
              }}
              className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
            >
              Show {codeString.split('\n').length - 8} more lines...
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Custom inline code component - renders as subtle inline code, NOT a block with header/copy button
const InlineCode: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="inline-code px-1.5 py-0.5 mx-0.5 bg-zinc-700/60 text-zinc-200 rounded text-sm font-mono border-0 whitespace-nowrap align-middle">
    {children}
  </code>
)

// Math component that handles both inline and block math
const MathComponent: React.FC<{ children: string; display?: boolean }> = ({ children, display }) => {
  try {
    if (display) {
      return (
        <div className="my-4 overflow-x-auto">
          <BlockMath math={children} />
        </div>
      )
    } else {
      return <InlineMath math={children} />
    }
  } catch (error) {
    console.error('KaTeX rendering error:', error)
    return (
      <span className="px-2 py-1 bg-red-900/20 text-red-400 rounded text-sm border border-red-700/50">
        Math rendering error: {children}
      </span>
    )
  }
}

// Process text to handle LaTeX math expressions
const processLatexInText = (text: string): React.ReactNode[] => {
  if (!text) return []

  // Pattern to match multiple LaTeX delimiters:
  // 1. Block math: $$...$$ and \[...\]
  // 2. Inline math: $...$ and \(...\)
  // 3. Bracket notation: [mathematical expressions with LaTeX commands]
  // 4. Parentheses math: (LaTeX expressions with commands like \mathbf, \frac, \partial, etc.)
  // 5. Arithmetic expressions: (any arithmetic expression with operators, variables, numbers)
  const blockMathRegex = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\])/g
  const inlineMathRegex = /(\$(?![$])[^$\n]*?\$(?![$])|\\\([\s\S]*?\\\))/g
  // Bracket math: [expression with LaTeX commands or mathematical notation] - detect mathematical expressions in brackets
  const bracketMathRegex = /\[\s*\\?[^[\]]*?(?:\\[a-zA-Z]+|[(){}=+\-*/^_'x]|u\(|v\(|dx|dy|dt|[a-zA-Z]'?\([a-zA-Z]\))[^[\]]*?\s*\]/g
  // Parentheses math/arithmetic: (LaTeX expression OR arithmetic expression)
  // Matches:
  // - LaTeX commands: \mathbf, \frac, \partial, \nabla, etc.
  // - Arithmetic expressions: numbers, variables, operators (+, -, *, /, =, <, >, ≤, ≥, ^, %)
  // - Functions: sin, cos, tan, log, ln, exp, sqrt, etc.
  // - Mathematical notation: subscripts (x_1), superscripts (x^2), fractions
  // - Simple arithmetic: (2+3), (x=y), (a*b), etc.
  const parenMathRegex = /\([^)]*(?:\\[a-zA-Z]+|[\d\w]+\s*[+\-*/=<>≤≥^%]\s*[\d\w]+|[\d\w]+\s*[+\-*/=<>≤≥^%]|sin|cos|tan|log|ln|exp|sqrt|[\d\w]+\^[\d\w]+|[\d\w]+_[\d\w]+|[\d.]+[+\-*/=<>≤≥^%][\d.]+)[^)]*\)/g

  const parts: Array<{ type: 'text' | 'block-math' | 'inline-math' | 'bracket-math' | 'paren-math'; content: string; start: number; end: number }> = []

  // First, find all block math matches
  let match
  const blockMatches: Array<{ start: number; end: number; content: string }> = []
  blockMathRegex.lastIndex = 0
  while ((match = blockMathRegex.exec(text)) !== null) {
    blockMatches.push({
      start: match.index,
      end: match.index + match[0].length,
      content: match[0]
    })
  }

  // Find bracket math matches that don't overlap with block math
  const bracketMatches: Array<{ start: number; end: number; content: string }> = []
  bracketMathRegex.lastIndex = 0
  while ((match = bracketMathRegex.exec(text)) !== null) {
    const isInsideBlock = blockMatches.some(
      (bm) => match.index >= bm.start && match.index < bm.end
    )
    if (!isInsideBlock) {
      bracketMatches.push({
        start: match.index,
        end: match.index + match[0].length,
        content: match[0]
      })
    }
  }

  // Find parentheses math/arithmetic matches that don't overlap with block math or bracket math
  const parenMatches: Array<{ start: number; end: number; content: string }> = []
  parenMathRegex.lastIndex = 0
  while ((match = parenMathRegex.exec(text)) !== null) {
    const isInsideBlock = blockMatches.some(
      (bm) => match.index >= bm.start && match.index < bm.end
    )
    const isInsideBracket = bracketMatches.some(
      (bm) => match.index >= bm.start && match.index < bm.end
    )
    const content = match[0]
    // Check if it contains LaTeX commands OR arithmetic expressions
    const hasLatexCommand = /\\[a-zA-Z]+/.test(content)
    const hasArithmetic = /[\d\w]+\s*[+\-*/=<>≤≥^%]\s*[\d\w]+|[\d.]+[+\-*/=<>≤≥^%][\d.]+|sin|cos|tan|log|ln|exp|sqrt|[\d\w]+\^[\d\w]+|[\d\w]+_[\d\w]+/.test(content)
    if (!isInsideBlock && !isInsideBracket && (hasLatexCommand || hasArithmetic)) {
      parenMatches.push({
        start: match.index,
        end: match.index + match[0].length,
        content: match[0]
      })
    }
  }

  // Then find inline math matches that don't overlap with block math, bracket math, or paren math
  const inlineMatches: Array<{ start: number; end: number; content: string }> = []
  inlineMathRegex.lastIndex = 0
  while ((match = inlineMathRegex.exec(text)) !== null) {
    const isInsideBlock = blockMatches.some(
      (bm) => match.index >= bm.start && match.index < bm.end
    )
    const isInsideBracket = bracketMatches.some(
      (bm) => match.index >= bm.start && match.index < bm.end
    )
    const isInsideParen = parenMatches.some(
      (pm) => match.index >= pm.start && match.index < pm.end
    )
    if (!isInsideBlock && !isInsideBracket && !isInsideParen) {
      inlineMatches.push({
        start: match.index,
        end: match.index + match[0].length,
        content: match[0]
      })
    }
  }

  // Combine and sort all matches
  const allMatches = [
    ...blockMatches.map(m => ({ ...m, type: 'block-math' as const })),
    ...bracketMatches.map(m => ({ ...m, type: 'bracket-math' as const })),
    ...parenMatches.map(m => ({ ...m, type: 'paren-math' as const })),
    ...inlineMatches.map(m => ({ ...m, type: 'inline-math' as const }))
  ].sort((a, b) => a.start - b.start)

  // Build parts array
  let lastIndex = 0
  for (const mathMatch of allMatches) {
    // Add text before this match
    if (mathMatch.start > lastIndex) {
      const textContent = text.substring(lastIndex, mathMatch.start)
      if (textContent.trim()) {
        parts.push({ type: 'text', content: textContent, start: lastIndex, end: mathMatch.start })
      }
    }

    // Add the math match
    parts.push({
      type: mathMatch.type,
      content: mathMatch.content,
      start: mathMatch.start,
      end: mathMatch.end
    })

    lastIndex = mathMatch.end
  }

  // Add remaining text
  if (lastIndex < text.length) {
    const textContent = text.substring(lastIndex)
    if (textContent.trim()) {
      parts.push({ type: 'text', content: textContent, start: lastIndex, end: text.length })
    }
  }

  // If no matches found, return the whole text as a single part
  if (parts.length === 0) {
    parts.push({ type: 'text', content: text, start: 0, end: text.length })
  }

  // Convert to React nodes
  return parts.map((part, index) => {
    if (part.type === 'block-math') {
      // Handle both $$...$$ and \[...\]
      let mathContent = part.content.trim()
      if (mathContent.startsWith('$$') && mathContent.endsWith('$$')) {
        mathContent = mathContent.slice(2, -2).trim()
      } else if (mathContent.startsWith('\\[') && mathContent.endsWith('\\]')) {
        mathContent = mathContent.slice(2, -2).trim()
      }
      return <MathComponent key={index} display={true}>{mathContent}</MathComponent>
    } else if (part.type === 'inline-math') {
      // Handle both $...$ and \(...\)
      let mathContent = part.content.trim()
      if (mathContent.startsWith('$') && mathContent.endsWith('$') && mathContent.length > 2) {
        mathContent = mathContent.slice(1, -1).trim()
      } else if (mathContent.startsWith('\\(') && mathContent.endsWith('\\)')) {
        mathContent = mathContent.slice(2, -2).trim()
      }
      return <MathComponent key={index} display={false}>{mathContent}</MathComponent>
    } else if (part.type === 'bracket-math') {
      // Handle [LaTeX expression] - treat as display math
      const mathContent = part.content.slice(1, -1).trim()
      return <MathComponent key={index} display={true}>{mathContent}</MathComponent>
    } else if (part.type === 'paren-math') {
      // Handle (LaTeX expression) - treat as inline math
      const mathContent = part.content.slice(1, -1).trim()
      return <MathComponent key={index} display={false}>{mathContent}</MathComponent>
    } else {
      return <span key={index}>{part.content}</span>
    }
  })
}

// Expandable container for long content
interface ExpandableContainerProps {
  children: React.ReactNode
  maxHeight?: number
}

const ExpandableContainer: React.FC<ExpandableContainerProps> = ({ children, maxHeight = 400 }) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const [contentHeight, setContentHeight] = useState(0)
  const contentRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight)
    }
  }, [children])

  const isLongContent = contentHeight > maxHeight
  const shouldTruncate = isLongContent && !isExpanded

  return (
    <>
      <div
        ref={contentRef}
        style={shouldTruncate ? { maxHeight: `${maxHeight}px`, overflow: 'hidden' } : {}}
      >
        {children}
      </div>
      {isLongContent && !isExpanded && (
        <div className="mt-3 pt-3 border-t border-zinc-700/30">
          <button
            onClick={() => setIsExpanded(true)}
            className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors font-medium"
          >
            Show more content ↓
          </button>
        </div>
      )}
    </>
  )
}

// Custom paragraph component that always uses div to avoid HTML nesting issues
// This prevents hydration errors from block-level elements (code blocks, math, etc.) inside <p> tags
const Paragraph: React.FC<{ children: React.ReactNode; node?: any }> = ({ children, node }) => {
  // For string content, process LaTeX
  if (typeof children === 'string') {
    const processed = processLatexInText(children)
    return <div className="mb-4 leading-relaxed text-zinc-200">{processed}</div>
  }

  // For all other content, use div to avoid nesting issues
  // (div can contain any block or inline elements, unlike p which is restricted)
  return <div className="mb-4 leading-relaxed text-zinc-200">{children}</div>
}

export const EnhancedMessageContent: React.FC<EnhancedMessageContentProps> = ({
  content,
  role,
  images,
  onCodePanelOpen
}) => {
  // Set global handler for code expansion
  React.useEffect(() => {
    if (onCodePanelOpen) {
      window.onCodePanelOpen = onCodePanelOpen
    }
    return () => {
      delete window.onCodePanelOpen
    }
  }, [onCodePanelOpen])

  return (
    <div className={cn(
      "prose prose-invert prose-zinc max-w-none",
      "prose-headings:text-zinc-100 prose-p:text-zinc-200 prose-strong:text-zinc-100",
      "prose-ul:text-zinc-200 prose-ol:text-zinc-200 prose-li:text-zinc-200",
      "prose-code:text-zinc-100 prose-pre:bg-zinc-900/50",
      role === 'user' ? "text-zinc-100" : "text-zinc-100"
    )}>
      {/* Image Display */}
      {images && images.length > 0 && (
        <ImageMessageDisplay images={images} />
      )}

      {/* Text Content */}
      {content && (
        <ExpandableContainer maxHeight={600}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }) {
                // Check inline flag first - this is the definitive indicator for single backticks
                if (inline) {
                  return <InlineCode>{children}</InlineCode>
                }

                // For block code, extract language from className (format: language-xxx)
                const match = /language-(\w+)/.exec(className || '')
                const language = match ? match[1] : null

                // If no language detected, render as inline code instead of a block with "TEXT" header
                if (!language && !className) {
                  return <InlineCode>{children}</InlineCode>
                }

                // Create a stable key from code content to prevent remounting
                const codeContent = String(children).replace(/\n$/, '')
                const codeKey = hashCode(codeContent)

                return (
                  <CodeBlock
                    key={`codeblock-${codeKey}`}
                    className={`language-${language || 'text'}`}
                  >
                    {children}
                  </CodeBlock>
                )
              },
              p: Paragraph,
              // Style other markdown elements
              h1: ({ children }) => <h1 className="text-2xl font-bold mb-4 mt-6 text-zinc-100 first:mt-0">{children}</h1>,
              h2: ({ children }) => <h2 className="text-xl font-semibold mb-3 mt-5 text-zinc-200 first:mt-0">{children}</h2>,
              h3: ({ children }) => <h3 className="text-lg font-medium mb-2 mt-4 text-zinc-200 first:mt-0">{children}</h3>,
              h4: ({ children }) => <h4 className="text-base font-medium mb-2 mt-3 text-zinc-200 first:mt-0">{children}</h4>,
              ul: ({ children }) => <ul className="list-disc pl-6 mb-4 space-y-2 text-zinc-200">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-6 mb-4 space-y-2 text-zinc-200">{children}</ol>,
              li: ({ children }) => <li className="text-zinc-200 leading-relaxed">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold text-zinc-100">{children}</strong>,
              em: ({ children }) => <em className="italic text-zinc-200">{children}</em>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-zinc-600 pl-4 italic text-zinc-300 my-4">
                  {children}
                </blockquote>
              ),
              a: ({ href, children }) => (
                <a href={href} className="text-blue-400 hover:text-blue-300 underline" target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto my-4">
                  <table className="w-full border-collapse border border-zinc-700 rounded-lg bg-zinc-900/50">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="bg-zinc-800/80">
                  {children}
                </thead>
              ),
              tbody: ({ children }) => (
                <tbody>
                  {children}
                </tbody>
              ),
              tr: ({ children }) => (
                <tr className="border-b border-zinc-700 hover:bg-zinc-800/30 transition-colors">
                  {children}
                </tr>
              ),
              th: ({ children }) => (
                <th className="border border-zinc-700 px-4 py-3 bg-zinc-800 text-zinc-200 font-semibold text-left">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="border border-zinc-700 px-4 py-2 text-zinc-300">
                  {children}
                </td>
              )
            }}
          >
            {content}
          </ReactMarkdown>
        </ExpandableContainer>
      )}
    </div>
  )
}

// Global type extension for the window object
declare global {
  interface Window {
    onCodePanelOpen?: (code: string, language: string) => void
  }
}