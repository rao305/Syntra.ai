'use client'

import * as React from 'react'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { cn } from '@/lib/utils'

interface ConversationLayoutProps {
  leftSidebar: React.ReactNode
  children: React.ReactNode
  rightPanel?: React.ReactNode
  defaultLeftSize?: number
  defaultRightSize?: number
  showRightPanel?: boolean
}

/**
 * ConversationLayout - 3-pane resizable layout for conversation interface
 *
 * Layout structure:
 * [Left Sidebar | Main Content | Right Panel (optional)]
 *
 * Features:
 * - Resizable panels with persistent state
 * - Collapsible sidebars
 * - Responsive behavior
 * - Keyboard accessible
 */
export function ConversationLayout({
  leftSidebar,
  children,
  rightPanel,
  defaultLeftSize = 20,
  defaultRightSize = 25,
  showRightPanel = true,
}: ConversationLayoutProps) {
  // Default to collapsed sidebar (closed by default)
  const [leftCollapsed, setLeftCollapsed] = React.useState(true)
  const [rightCollapsed, setRightCollapsed] = React.useState(false)

  // Load saved panel sizes from localStorage (only on client)
  React.useEffect(() => {
    if (typeof window === 'undefined') return
    
    const savedLeftSize = localStorage.getItem('conversation-left-panel-size')
    const savedRightSize = localStorage.getItem('conversation-right-panel-size')
    const savedLeftCollapsed = localStorage.getItem('conversation-left-collapsed')
    const savedRightCollapsed = localStorage.getItem('conversation-right-collapsed')

    // Only restore collapsed state if user has explicitly set it (not on first visit)
    if (savedLeftCollapsed !== null) {
      setLeftCollapsed(savedLeftCollapsed === 'true')
    }
    if (savedRightCollapsed) {
      setRightCollapsed(savedRightCollapsed === 'true')
    }
  }, [])

  const handleLeftCollapse = (collapsed: boolean) => {
    setLeftCollapsed(collapsed)
    if (typeof window !== 'undefined') {
      localStorage.setItem('conversation-left-collapsed', String(collapsed))
    }
  }

  const handleRightCollapse = (collapsed: boolean) => {
    setRightCollapsed(collapsed)
    if (typeof window !== 'undefined') {
      localStorage.setItem('conversation-right-collapsed', String(collapsed))
    }
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Main content area with 3-pane layout */}
      <ResizablePanelGroup
        direction="horizontal"
        className="flex-1 overflow-hidden"
        onLayout={(sizes) => {
          // Save panel sizes to localStorage (only on client)
          if (typeof window !== 'undefined') {
            if (sizes[0]) {
              localStorage.setItem('conversation-left-panel-size', String(sizes[0]))
            }
            if (sizes[2] && showRightPanel) {
              localStorage.setItem('conversation-right-panel-size', String(sizes[2]))
            }
          }
        }}
      >
        {/* Left Sidebar - Conversation List (collapsed by default) */}
        <ResizablePanel
          defaultSize={leftCollapsed ? 0 : defaultLeftSize}
          minSize={15}
          maxSize={35}
          collapsible
          collapsedSize={0}
          onCollapse={handleLeftCollapse}
          className={cn(
            'transition-all duration-200',
            leftCollapsed && 'min-w-0'
          )}
        >
          <div className="h-full bg-sidebar border-r border-sidebar-border overflow-hidden">
            {leftSidebar}
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle className="hover:bg-accent/50 transition-colors" />

        {/* Center Panel - Main Conversation View */}
        <ResizablePanel defaultSize={showRightPanel ? 55 : 80} minSize={30}>
          <div className="h-full bg-background overflow-hidden">
            {children}
          </div>
        </ResizablePanel>

        {/* Right Panel - Settings & Context */}
        {showRightPanel && rightPanel && (
          <>
            <ResizableHandle withHandle className="hover:bg-accent/50 transition-colors" />
            <ResizablePanel
              defaultSize={defaultRightSize}
              minSize={20}
              maxSize={40}
              collapsible
              collapsedSize={0}
              onCollapse={handleRightCollapse}
              className={cn(
                'transition-all duration-200',
                rightCollapsed && 'min-w-0'
              )}
            >
              <div className="h-full bg-card border-l border-border overflow-hidden">
                {rightPanel}
              </div>
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </div>
  )
}
