'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'

type Provider = 'perplexity' | 'openai' | 'gemini' | 'openrouter'

interface ProviderStatus {
  provider: string
  configured: boolean
  key_name?: string
  last_used?: string
  masked_key?: string
}

interface TestResult {
  provider: string
  success: boolean
  message: string
  details?: Record<string, any>
}

const PROVIDERS: { name: Provider; label: string; description: string }[] = [
  {
    name: 'perplexity',
    label: 'Perplexity',
    description: 'Web-grounded Q&A with citations',
  },
  {
    name: 'openai',
    label: 'OpenAI',
    description: 'GPT models for structured outputs',
  },
  {
    name: 'gemini',
    label: 'Gemini',
    description: 'Long-context models for large documents',
  },
  {
    name: 'openrouter',
    label: 'OpenRouter',
    description: 'Auto-routing and fallback',
  },
]

export default function ProvidersPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [orgId, setOrgId] = useState<string>('org_demo') // TODO: Get from session/auth
  const [providerStatuses, setProviderStatuses] = useState<ProviderStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [keyName, setKeyName] = useState('')
  const [saving, setSaving] = useState(false)
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})
  const [testing, setTesting] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin')
    }
  }, [status, router])

  useEffect(() => {
    if (session) {
      loadProviderStatuses()
    }
  }, [session])

  const loadProviderStatuses = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/orgs/${orgId}/providers/status`)
      if (response.ok) {
        const data = await response.json()
        setProviderStatuses(data)
      }
    } catch (error) {
      console.error('Failed to load provider statuses:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveKey = async (provider: Provider) => {
    if (!apiKey.trim()) return

    setSaving(true)
    try {
      const response = await fetch(`http://localhost:8000/api/orgs/${orgId}/providers`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          api_key: apiKey,
          key_name: keyName || null,
        }),
      })

      if (response.ok) {
        setApiKey('')
        setKeyName('')
        setEditingProvider(null)
        await loadProviderStatuses()
      } else {
        const error = await response.json()
        alert(`Failed to save API key: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to save API key:', error)
      alert('Failed to save API key')
    } finally {
      setSaving(false)
    }
  }

  const handleTestConnection = async (provider: Provider, useStored: boolean = true) => {
    setTesting({ ...testing, [provider]: true })
    try {
      const response = await fetch(`http://localhost:8000/api/orgs/${orgId}/providers/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          api_key: useStored ? null : apiKey,
        }),
      })

      if (response.ok) {
        const result = await response.json()
        setTestResults({ ...testResults, [provider]: result })
      } else {
        const error = await response.json()
        setTestResults({
          ...testResults,
          [provider]: {
            provider,
            success: false,
            message: error.detail || 'Test failed',
          },
        })
      }
    } catch (error) {
      console.error('Failed to test connection:', error)
      setTestResults({
        ...testResults,
        [provider]: {
          provider,
          success: false,
          message: 'Network error',
        },
      })
    } finally {
      setTesting({ ...testing, [provider]: false })
    }
  }

  if (status === 'loading' || loading) {
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
      <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Provider Settings</h1>
          <p className="mt-2 text-sm text-gray-600">
            Configure your API keys for different LLM providers. Keys are encrypted at rest.
          </p>
        </div>

        <div className="space-y-6">
          {PROVIDERS.map((provider) => {
            const status = providerStatuses.find((s) => s.provider === provider.name)
            const isEditing = editingProvider === provider.name
            const testResult = testResults[provider.name]
            const isTesting = testing[provider.name]

            return (
              <div
                key={provider.name}
                className="bg-white shadow rounded-lg p-6 border border-gray-200"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold text-gray-900">{provider.label}</h3>
                      {status?.configured && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Configured
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-600">{provider.description}</p>

                    {status?.configured && (
                      <div className="mt-3 space-y-1 text-sm">
                        <p className="text-gray-600">
                          <span className="font-medium">Key:</span>{' '}
                          <code className="px-2 py-1 bg-gray-100 rounded text-xs">
                            {status.masked_key}
                          </code>
                        </p>
                        {status.key_name && (
                          <p className="text-gray-600">
                            <span className="font-medium">Name:</span> {status.key_name}
                          </p>
                        )}
                        {status.last_used && (
                          <p className="text-gray-600">
                            <span className="font-medium">Last used:</span>{' '}
                            {new Date(status.last_used).toLocaleString()}
                          </p>
                        )}
                      </div>
                    )}

                    {isEditing && (
                      <div className="mt-4 space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            API Key
                          </label>
                          <input
                            type="password"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder={`Enter ${provider.label} API key`}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Key Name (optional)
                          </label>
                          <input
                            type="text"
                            value={keyName}
                            onChange={(e) => setKeyName(e.target.value)}
                            placeholder="e.g., Production Key"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSaveKey(provider.name)}
                            disabled={saving || !apiKey.trim()}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {saving ? 'Saving...' : 'Save Key'}
                          </button>
                          {apiKey.trim() && (
                            <button
                              onClick={() => handleTestConnection(provider.name, false)}
                              disabled={isTesting}
                              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                            >
                              {isTesting ? 'Testing...' : 'Test Before Saving'}
                            </button>
                          )}
                          <button
                            onClick={() => {
                              setEditingProvider(null)
                              setApiKey('')
                              setKeyName('')
                            }}
                            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {testResult && (
                      <div
                        className={`mt-4 p-3 rounded-md ${
                          testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                        }`}
                      >
                        <p
                          className={`text-sm font-medium ${
                            testResult.success ? 'text-green-800' : 'text-red-800'
                          }`}
                        >
                          {testResult.success ? '✓' : '✗'} {testResult.message}
                        </p>
                        {testResult.details && (
                          <pre className="mt-2 text-xs text-gray-600">
                            {JSON.stringify(testResult.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="ml-4 flex flex-col gap-2">
                    {!isEditing && (
                      <>
                        <button
                          onClick={() => setEditingProvider(provider.name)}
                          className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                        >
                          {status?.configured ? 'Update' : 'Configure'}
                        </button>
                        {status?.configured && (
                          <button
                            onClick={() => handleTestConnection(provider.name, true)}
                            disabled={isTesting}
                            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                          >
                            {isTesting ? 'Testing...' : 'Test Connection'}
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
