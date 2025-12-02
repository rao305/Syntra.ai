"use client"

import { useState } from 'react'
import { EnhancedSidebar } from '@/components/enhanced-sidebar'
import { EnhancedChatInterface } from '@/components/enhanced-chat-interface'
import { CollabPanel, type CollabPanelState } from '@/components/collaborate/CollabPanel'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  chainOfThought?: string
  timestamp?: string
  modelId?: string
  modelName?: string
  reasoningType?: 'coding' | 'analysis' | 'creative' | 'research' | 'conversation'
  confidence?: number
  processingTime?: number
}

interface ChatHistoryItem {
  id: string
  firstLine: string
  timestamp: string
}

interface EnhancedConversationLayoutProps {
  messages: Message[]
  history: ChatHistoryItem[]
  onSendMessage: (content: string, images?: any[]) => Promise<void>
  onUpdateMessage?: (messageId: string, updates: Partial<Message>) => void
  onNewChat: () => void
  onHistoryClick: (id: string) => void
  isLoading: boolean
  selectedModel: string
  onModelSelect: (modelId: string) => void
  onContinueWorkflow?: () => void
  autoRoutedModel?: string | null
  collabPanel?: CollabPanelState
}

export function EnhancedConversationLayout({
  messages,
  history,
  onSendMessage,
  onUpdateMessage,
  onNewChat,
  onHistoryClick,
  isLoading,
  selectedModel,
  onModelSelect,
  onContinueWorkflow,
  autoRoutedModel,
  collabPanel
}: EnhancedConversationLayoutProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const user = null

  return (
    <div className="flex h-screen w-full bg-zinc-900 text-zinc-50 overflow-hidden font-sans">
      <EnhancedSidebar
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
        history={history}
        onNewChat={onNewChat}
        onHistoryClick={onHistoryClick}
        user={user}
      />
      <main className="flex-1 flex flex-col h-full relative transition-all duration-300 ease-in-out">
        <EnhancedChatInterface
          messages={messages}
          onSendMessage={onSendMessage}
          onUpdateMessage={onUpdateMessage}
          isLoading={isLoading}
          selectedModel={selectedModel}
          onModelSelect={onModelSelect}
          onContinueWorkflow={onContinueWorkflow}
          autoRoutedModel={autoRoutedModel}
          collabPanel={collabPanel}
        />
      </main>
    </div>
  )
}
