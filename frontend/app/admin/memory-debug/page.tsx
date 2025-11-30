'use client'

/**
 * Memory Debug Admin Page
 * 
 * DEV / ADMIN TOOL - Read-only memory inspection
 * 
 * This page allows admins to inspect what has been stored in Supermemory
 * for debugging and monitoring purposes.
 * 
 * WARNING: This shows internal memory data and should NOT be exposed to normal end-users.
 */

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Search, AlertTriangle, Loader2 } from 'lucide-react'

interface Memory {
  id: string
  text: string
  createdAt?: string
  metadata?: Record<string, any>
}

interface MemoryDebugResponse {
  userId?: string
  sessionId?: string
  query?: string
  memories: Memory[]
  error?: string
}

export default function MemoryDebugPage() {
  const [userId, setUserId] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MemoryDebugResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const params = new URLSearchParams()
      if (userId) params.append('userId', userId)
      if (sessionId) params.append('sessionId', sessionId)
      if (query) params.append('query', query)

      const response = await fetch(`/api/memory-debug?${params.toString()}`)
      const data: MemoryDebugResponse = await response.json()

      if (!response.ok) {
        setError(data.error || `Error ${response.status}: ${response.statusText}`)
        return
      }

      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch memories')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Memory Debug</h1>
        <p className="text-muted-foreground">
          DEV / ADMIN TOOL – Inspect Supermemory storage for debugging
        </p>
      </div>

      <Alert className="mb-6 border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Admin Only</AlertTitle>
        <AlertDescription>
          This page shows internal memory data and should NOT be exposed to normal end-users.
          Use this tool only for debugging and monitoring Supermemory behavior.
        </AlertDescription>
      </Alert>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Search Memories</CardTitle>
          <CardDescription>
            Enter userId, sessionId, or a search query to find stored memories
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="userId">User ID</Label>
                <Input
                  id="userId"
                  placeholder="e.g., test-user-1"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
              </div>
              <div>
                <Label htmlFor="sessionId">Session ID</Label>
                <Input
                  id="sessionId"
                  placeholder="e.g., session-1"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
              </div>
              <div>
                <Label htmlFor="query">Search Query</Label>
                <Input
                  id="query"
                  placeholder="e.g., Alex TypeScript"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
              </div>
            </div>
            <Button onClick={handleSearch} disabled={loading} className="w-full md:w-auto">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  Search Memories
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
            <CardDescription>
              Found {result.memories.length} memory{result.memories.length !== 1 ? 'ies' : ''}
              {result.userId && ` for userId: ${result.userId}`}
              {result.sessionId && ` in session: ${result.sessionId}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {result.memories.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                No memories found. Try adjusting your search criteria.
              </p>
            ) : (
              <div className="space-y-4">
                {result.memories.map((memory) => (
                  <Card key={memory.id} className="bg-muted/50">
                    <CardContent className="pt-6">
                      <div className="space-y-2">
                        <div className="flex items-start justify-between">
                          <p className="text-sm font-medium">Memory ID: {memory.id}</p>
                          {memory.createdAt && (
                            <span className="text-xs text-muted-foreground">
                              {new Date(memory.createdAt).toLocaleString()}
                            </span>
                          )}
                        </div>
                        <p className="text-sm whitespace-pre-wrap">{memory.text}</p>
                        {memory.metadata && Object.keys(memory.metadata).length > 0 && (
                          <details className="mt-2">
                            <summary className="text-xs text-muted-foreground cursor-pointer">
                              Metadata
                            </summary>
                            <pre className="mt-2 text-xs bg-background p-2 rounded overflow-auto">
                              {JSON.stringify(memory.metadata, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}








