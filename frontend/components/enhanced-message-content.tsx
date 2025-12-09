'use client'

import { ImageMessageDisplay } from '@/components/image-message-display'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import 'katex/dist/katex.min.css'
import { Check, Copy, Maximize2 } from 'lucide-react'
import React, { useState } from 'react'
import { BlockMath, InlineMath } from 'react-katex'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

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

// Custom code block component
const CodeBlock: React.FC<CodeBlockProps> = ({ children, className }) => {
  const [copied, setCopied] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const language = className?.replace('language-', '') || 'text'
  const codeString = String(children).replace(/\n$/, '')
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
            onClick={handleExpand}
            className="h-6 px-2 text-xs text-blue-400 hover:text-blue-300 hover:bg-blue-900/20 transition-colors"
          >
            <Maximize2 className="w-3 h-3 mr-1" />
            Expand
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
              onClick={() => setIsExpanded(true)}
              className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Show {codeString.split('\n').length - 8} more lines...
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Custom inline code component
const InlineCode: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="px-1.5 py-0.5 rounded bg-zinc-800/80 text-zinc-200 text-sm font-mono border border-zinc-700/50">
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
  const blockMathRegex = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\])/g
  const inlineMathRegex = /(\$(?![$])[^$\n]*?\$(?![$])|\\\([\s\S]*?\\\))/g
  // Bracket math: [expression with LaTeX commands or mathematical notation] - detect mathematical expressions in brackets
  const bracketMathRegex = /\[\s*\\?[^[\]]*?(?:\\[a-zA-Z]+|[(){}=+\-*/^_'x]|u\(|v\(|dx|dy|dt|[a-zA-Z]'?\([a-zA-Z]\))[^[\]]*?\s*\]/g

  const parts: Array<{ type: 'text' | 'block-math' | 'inline-math' | 'bracket-math'; content: string; start: number; end: number }> = []

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

  // Then find inline math matches that don't overlap with block math or bracket math
  const inlineMatches: Array<{ start: number; end: number; content: string }> = []
  inlineMathRegex.lastIndex = 0
  while ((match = inlineMathRegex.exec(text)) !== null) {
    const isInsideBlock = blockMatches.some(
      (bm) => match.index >= bm.start && match.index < bm.end
    )
    const isInsideBracket = bracketMatches.some(
      (bm) => match.index >= bm.start && match.index < bm.end
    )
    if (!isInsideBlock && !isInsideBracket) {
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
    } else {
      return <span key={index}>{part.content}</span>
    }
  })
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
        <ReactMarkdown
          components={{
            code({ node, inline, className, children, ...props }) {
              if (inline) {
                return <InlineCode>{children}</InlineCode>
              }
              return (
                <CodeBlock className={className}>
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
                <table className="min-w-full border border-zinc-700 rounded-lg">
                  {children}
                </table>
              </div>
            ),
            th: ({ children }) => (
              <th className="border border-zinc-700 px-3 py-2 bg-zinc-800 text-zinc-200 font-medium text-left">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="border border-zinc-700 px-3 py-2 text-zinc-300">
                {children}
              </td>
            )
          }}
        >
          {content}
        </ReactMarkdown>
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