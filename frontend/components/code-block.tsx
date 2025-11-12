'use client'

import * as React from 'react'
import { Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface CodeBlockProps {
  code: string
  language?: string
  className?: string
}

/**
 * CodeBlock - Enhanced code display with copy functionality
 * 
 * Features:
 * - Language label
 * - Copy button with feedback
 * - Syntax highlighting ready (can be enhanced with prism/react-syntax-highlighter)
 * - Dark theme styling
 */
export function CodeBlock({ code, language, className }: CodeBlockProps) {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy code:', err)
    }
  }

  return (
    <div
      className={cn(
        'relative rounded-lg border border-border/50 bg-zinc-950/50 overflow-hidden',
        className
      )}
    >
      {/* Header with language and copy button */}
      <div className="flex items-center justify-between px-4 py-2 bg-zinc-900/50 border-b border-border/30">
        {language && (
          <span className="text-xs font-mono text-muted-foreground uppercase">
            {language}
          </span>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-7 px-2 text-xs hover:bg-zinc-800/50"
          aria-label="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 mr-1.5" />
              Copied
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 mr-1.5" />
              Copy code
            </>
          )}
        </Button>
      </div>

      {/* Code content */}
      <div className="relative">
        <pre className="p-4 overflow-x-auto text-sm leading-relaxed">
          <code className="font-mono text-zinc-100 whitespace-pre">{code}</code>
        </pre>
      </div>
    </div>
  )
}

