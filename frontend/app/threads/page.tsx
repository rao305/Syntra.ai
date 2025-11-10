'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'

type Provider = 'perplexity' | 'openai' | 'gemini' | 'openrouter'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  provider?: Provider
  timestamp: Date
}

const PROVIDER_COLORS: Record<Provider, string> = {
  perplexity: 'bg-purple-100 text-purple-800 border-purple-200',
  openai: 'bg-green-100 text-green-800 border-green-200',
  gemini: 'bg-blue-100 text-blue-800 border-blue-200',
  openrouter: 'bg-orange-100 text-orange-800 border-orange-200',
}

const PROVIDER_LABELS: Record<Provider, string> = {
  perplexity: 'Perplexity',
  openai: 'OpenAI',
  gemini: 'Gemini',
  openrouter: 'OpenRouter',
}

export default function ThreadsPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [selectedProvider, setSelectedProvider] = useState<Provider>('perplexity')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin')
    }
  }, [status, router])

  const handleSendMessage = async () => {
    if (!input.trim() || sending) return

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages([...messages, userMessage])
    setInput('')
    setSending(true)

    // TODO Phase 2: Replace with actual API call to /threads/{id}/messages
    // Simulating response for Phase 1 dogfooding
    setTimeout(() => {
      const assistantMessage: Message = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: `[Phase 1 Stub] This is a simulated response from ${PROVIDER_LABELS[selectedProvider]}. In Phase 2, this will be a real LLM response using your configured API keys.`,
        provider: selectedProvider,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
      setSending(false)
    }, 1000)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  if (!session) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto h-screen flex flex-col">
        {/* Header */}
        <div className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Thread</h1>
          <p className="text-sm text-gray-600 mt-1">
            Phase 1 stub - Full threading in Phase 2
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">No messages yet</p>
              <p className="text-gray-400 text-sm mt-2">
                Start a conversation by typing a message below
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-200'
                  }`}
                >
                  {message.provider && (
                    <div className="mb-2">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                          PROVIDER_COLORS[message.provider]
                        }`}
                      >
                        {PROVIDER_LABELS[message.provider]}
                      </span>
                    </div>
                  )}
                  <p className={message.role === 'user' ? 'text-white' : 'text-gray-900'}>
                    {message.content}
                  </p>
                  <p
                    className={`text-xs mt-2 ${
                      message.role === 'user' ? 'text-blue-100' : 'text-gray-400'
                    }`}
                  >
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))
          )}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="animate-pulse">●</div>
                  <span className="text-gray-500 text-sm">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="bg-white border-t border-gray-200 p-6">
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Provider
            </label>
            <div className="flex gap-2">
              {(Object.keys(PROVIDER_LABELS) as Provider[]).map((provider) => (
                <button
                  key={provider}
                  onClick={() => setSelectedProvider(provider)}
                  className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                    selectedProvider === provider
                      ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                      : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {PROVIDER_LABELS[provider]}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
              rows={2}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              disabled={sending}
            />
            <button
              onClick={handleSendMessage}
              disabled={!input.trim() || sending}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {sending ? 'Sending...' : 'Send'}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Note: This is a Phase 1 stub. Real LLM integration coming in Phase 2.
          </p>
        </div>
      </div>
    </div>
  )
}
