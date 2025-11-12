'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiFetch, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CheckCircle2, XCircle, Loader2, AlertCircle, Key, Activity } from 'lucide-react'

type Provider = 'perplexity' | 'openai' | 'gemini' | 'openrouter'

interface ProviderStatus {
  provider: string
  configured: boolean
  key_name?: string
  last_used?: string
  masked_key?: string
  usage?: {
    requests_today: number
    tokens_today: number
    request_limit: number
    token_limit: number
  }
}

interface MemoryStatus {
  enabled: boolean
  message: string
  last_checked?: string
}

interface TestResult {
  provider: Provider
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

export function ProvidersPage() {
  const [providerStatuses, setProviderStatuses] = useState<ProviderStatus[]>([])
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [keyName, setKeyName] = useState('')
  const [saving, setSaving] = useState(false)
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})
  const [testing, setTesting] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const orgId = 'org_demo' // Dev mode: use demo org

  const loadProviderStatuses = useCallback(async () => {
    setLoading(true)
    try {
      const response = await apiFetch(`/orgs/${orgId}/providers/status`, orgId)
      const data: { providers: ProviderStatus[]; memory_status?: MemoryStatus } = await response.json()
      setProviderStatuses(data.providers || [])
      setMemoryStatus(data.memory_status || null)
    } catch (error) {
      console.error('Failed to load provider statuses:', error)
      setError('Failed to load provider statuses')
    } finally {
      setLoading(false)
    }
  }, [orgId])

  useEffect(() => {
    loadProviderStatuses()
  }, [loadProviderStatuses])

  const handleSaveKey = async (provider: Provider) => {
    if (!apiKey.trim()) return

    setSaving(true)
    setError(null)
    try {
      await apiFetch(`/orgs/${orgId}/providers`, orgId, {
        method: 'POST',
        body: JSON.stringify({
          provider,
          api_key: apiKey,
          key_name: keyName || null,
        }),
      })

      setApiKey('')
      setKeyName('')
      setEditingProvider(null)
      await loadProviderStatuses()
    } catch (error) {
      console.error('Failed to save API key:', error)
      if (error instanceof ApiError) {
        setError(error.message)
      } else {
        setError('Failed to save API key')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleTestConnection = async (provider: Provider, useStored: boolean = true) => {
    setTesting((prev) => ({ ...prev, [provider]: true }))
    setError(null)
    try {
      const response = await apiFetch(`/orgs/${orgId}/providers/test`, orgId, {
        method: 'POST',
        body: JSON.stringify({
          provider,
          api_key: useStored ? null : apiKey,
        }),
      })

      const result: TestConnectionResponse = await response.json()
      setTestResults((prev) => ({
        ...prev,
        [provider]: {
          provider,
          success: result.success,
          message: result.message,
          details: result.details,
        },
      }))
    } catch (error) {
      console.error('Failed to test connection:', error)
      setTestResults((prev) => ({
        ...prev,
        [provider]: {
          provider,
          success: false,
          message: error instanceof ApiError ? error.message : 'Network error',
        },
      }))
    } finally {
      setTesting((prev) => ({ ...prev, [provider]: false }))
    }
  }

  const getProviderStatus = (provider: Provider): ProviderStatus | undefined => {
    return providerStatuses.find((p) => p.provider === provider)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {memoryStatus && (
        <Card className="border-border bg-zinc-900/40 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Memory Status
            </CardTitle>
            <CardDescription>Vector database health check</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {memoryStatus.enabled ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-red-500" />
              )}
              <span className={memoryStatus.enabled ? 'text-green-500' : 'text-red-500'}>
                {memoryStatus.message}
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6">
        {PROVIDERS.map((provider) => {
          const status = getProviderStatus(provider.name)
          const isEditing = editingProvider === provider.name
          const testResult = testResults[provider.name]

          return (
            <Card key={provider.name} className="border-border bg-zinc-900/40 backdrop-blur-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {provider.label}
                      {status?.configured && (
                        <Badge variant="outline" className="bg-green-500/20 text-green-300 border-green-500/30">
                          Configured
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription>{provider.description}</CardDescription>
                  </div>
                  {status?.configured && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestConnection(provider.name, true)}
                      disabled={testing[provider.name]}
                    >
                      {testing[provider.name] ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        'Test'
                      )}
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {testResult && (
                  <Alert variant={testResult.success ? 'default' : 'destructive'}>
                    {testResult.success ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <XCircle className="h-4 w-4" />
                    )}
                    <AlertDescription>{testResult.message}</AlertDescription>
                  </Alert>
                )}

                {status?.usage && (
                  <div className="grid grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
                    <div>
                      <div className="text-sm text-muted-foreground">Requests Today</div>
                      <div className="text-lg font-semibold">
                        {status.usage.requests_today} / {status.usage.request_limit}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Tokens Today</div>
                      <div className="text-lg font-semibold">
                        {status.usage.tokens_today.toLocaleString()} / {status.usage.token_limit.toLocaleString()}
                      </div>
                    </div>
                  </div>
                )}

                {status?.key_name && (
                  <div className="text-sm text-muted-foreground">
                    Key name: <span className="text-foreground">{status.key_name}</span>
                  </div>
                )}

                {isEditing ? (
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="api-key">API Key</Label>
                      <Input
                        id="api-key"
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="Enter your API key"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label htmlFor="key-name">Key Name (Optional)</Label>
                      <Input
                        id="key-name"
                        type="text"
                        value={keyName}
                        onChange={(e) => setKeyName(e.target.value)}
                        placeholder="e.g., Production Key"
                        className="mt-1"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleSaveKey(provider.name)}
                        disabled={!apiKey.trim() || saving}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      >
                        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
                        Save
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setEditingProvider(null)
                          setApiKey('')
                          setKeyName('')
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant={status?.configured ? 'outline' : 'default'}
                    onClick={() => setEditingProvider(provider.name)}
                    className={!status?.configured ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : ''}
                  >
                    {status?.configured ? 'Update Key' : 'Add Key'}
                  </Button>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

interface TestConnectionResponse {
  provider: string
  success: boolean
  message: string
  details?: Record<string, any>
}

