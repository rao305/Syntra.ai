import React from 'react'

export function MessageSkeleton() {
  return (
    <div className="flex gap-4 justify-start animate-pulse">
      <div className="w-8 h-8 rounded-lg bg-accent/10" />
      <div className="bg-card border border-border p-4 rounded-lg rounded-bl-none max-w-md space-y-2">
        <div className="h-4 bg-muted rounded w-3/4" />
        <div className="h-4 bg-muted rounded w-1/2" />
      </div>
    </div>
  )
}

export function ChatInterfaceSkeleton() {
  return (
    <div className="min-h-screen bg-background pt-24 pb-12">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <div className="space-y-6">
          <div className="text-center space-y-2 animate-pulse">
            <div className="h-10 bg-muted rounded w-48 mx-auto" />
            <div className="h-6 bg-muted rounded w-64 mx-auto" />
          </div>

          <div className="flex items-center justify-between p-4 bg-card border border-border rounded-lg animate-pulse">
            <div className="h-8 bg-muted rounded w-64" />
          </div>

          <div className="flex flex-col h-[600px] bg-background rounded-lg border border-border overflow-hidden">
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <MessageSkeleton />
              <MessageSkeleton />
              <MessageSkeleton />
            </div>

            <div className="border-t border-border p-4 bg-card/30">
              <div className="flex gap-3 animate-pulse">
                <div className="flex-1 h-10 bg-muted rounded-lg" />
                <div className="w-10 h-10 bg-muted rounded-lg" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}









