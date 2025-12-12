'use client'

import { Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CollaborationButtonProps {
  query: string
  orgId: string
  onCollaborate: (query: string, orgId: string) => void
  disabled?: boolean
  className?: string
  title?: string
}

export function CollaborationButton({
  query,
  orgId,
  onCollaborate,
  disabled = false,
  className,
  title,
}: CollaborationButtonProps) {
  const handleClick = () => {
    onCollaborate(query, orgId)
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled || !query.trim()}
      title={title}
      className={cn(
        'inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm',
        'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800',
        'dark:from-blue-700 dark:to-blue-800 dark:hover:from-blue-800 dark:hover:to-blue-900',
        'text-white shadow-lg hover:shadow-xl transition-all',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg',
        className
      )}
    >
      <Zap className="w-4 h-4" />
      Collaborate
    </button>
  )
}
