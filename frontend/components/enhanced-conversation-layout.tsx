"use client"

import { type CollabPanelState } from '@/components/collaborate/CollabPanel'
import { EnhancedChatInterface } from '@/components/enhanced-chat-interface'
import { EnhancedSidebar } from '@/components/enhanced-sidebar'
import { useState } from 'react'

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
  onDeleteChat?: (id: string) => void
  onRenameChat?: (id: string, newName: string) => void
  isLoading: boolean
  selectedModel: string
  onModelSelect: (modelId: string) => void
  onContinueWorkflow?: () => void
  autoRoutedModel?: string | null
  collabPanel?: CollabPanelState
  currentThreadId?: string | null
  useNewThreadsSystem?: boolean
}

export function EnhancedConversationLayout({
  messages,
  history,
  onSendMessage,
  onUpdateMessage,
  onNewChat,
  onHistoryClick,
  onDeleteChat,
  onRenameChat,
  isLoading,
  selectedModel,
  onModelSelect,
  onContinueWorkflow,
  autoRoutedModel,
  collabPanel,
  currentThreadId = null,
  useNewThreadsSystem = true,
}: EnhancedConversationLayoutProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const user = null

  return (
    <div className="flex h-screen w-full bg-gradient-to-br from-zinc-950 via-zinc-900 to-black text-zinc-50 overflow-hidden font-sans">
      <EnhancedSidebar
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
        history={history}
        onNewChat={onNewChat}
        onHistoryClick={onHistoryClick}
        onDeleteChat={onDeleteChat}
        onRenameChat={onRenameChat}
        user={user}
        currentThreadId={currentThreadId}
        useNewThreadsSystem={useNewThreadsSystem}
      />
      <main className="flex-1 flex flex-col h-full relative transition-all duration-300 ease-in-out bg-gradient-to-br from-zinc-950 via-zinc-900 to-black">
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
