"use client"

import { useAuth } from "@/components/auth/auth-provider"
import { ChatSearch } from "@/components/chat-search"
import { ThreadItem } from "@/components/thread-item"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useThreads, type Thread } from "@/hooks/use-threads"
import { getDateGroupLabel, groupThreadsByDate } from "@/lib/date-utils"
import { cn } from "@/lib/utils"
import { useUser } from "@clerk/nextjs"
import { Archive, ChevronsUpDown, Clock, Edit2, ExternalLink, LogOut, MoreVertical, PanelLeft, Pin, Plus, Trash2 } from "lucide-react"
import { usePathname, useRouter } from "next/navigation"
import * as React from "react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

interface SidebarProps {
  isCollapsed: boolean
  setIsCollapsed: (collapsed: boolean) => void
  history?: ChatHistoryItem[] // Legacy prop - kept for backward compatibility
  onNewChat?: () => void
  onHistoryClick?: (id: string) => void
  onDeleteChat?: (id: string) => void
  onRenameChat?: (id: string, newName: string) => void
  user?: any
  currentThreadId?: string | null // To highlight active thread
  useNewThreadsSystem?: boolean // Feature flag to use new system
}

interface ChatHistoryItem {
  id: string
  firstLine: string
  timestamp: string
}

export function EnhancedSidebar({
  isCollapsed,
  setIsCollapsed,
  history = [],
  onNewChat,
  onHistoryClick,
  onDeleteChat,
  onRenameChat,
  user: propUser,
  currentThreadId = null,
  useNewThreadsSystem = true, // Default to new system
}: SidebarProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { user: authUser, signOut } = useAuth()
  const { user: clerkUser } = useUser()
  const [renameId, setRenameId] = React.useState<string | null>(null)
  const [renameName, setRenameName] = React.useState('')
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<Thread[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showArchived, setShowArchived] = useState(false)

  // Use auth user or fallback to prop user
  const user = authUser || propUser

  const handleRenameSubmit = (id: string) => {
    if (renameName.trim()) {
      onRenameChat?.(id, renameName.trim())
      setRenameId(null)
      setRenameName('')
    }
  }

  // Use new threads system or legacy history
  const {
    threads,
    isLoading,
    searchThreads,
    archiveThread,
    deleteThread,
    deleteAllThreads,
    updateThreadTitle,
    pinThread,
    mutate: refreshThreads,
  } = useThreads()

  // Refresh threads ONLY when creating a new thread (after redirect from new conversation)
  // Don't refresh on every thread navigation to avoid jitter when switching between chats
  useEffect(() => {
    if (pathname === '/conversations/new') {
      // We're on the new conversation page - don't refresh yet
      return
    }

    // Only refresh if we came from the new page to show the newly created thread
    // This happens when user creates a new chat and is redirected to the new thread
    // We check if there's a new thread ID that's not in our list yet
    if (pathname?.startsWith('/conversations/') && pathname !== '/conversations') {
      const threadIdFromPath = pathname.split('/conversations/')[1]
      // Check if this thread ID exists in our current threads list
      const threadExists = threads.some(t => t.id === threadIdFromPath)

      // Only refresh if the thread doesn't exist yet (meaning it was just created)
      if (!threadExists && threadIdFromPath && threadIdFromPath !== 'new') {
        const timer = setTimeout(() => {
          refreshThreads()
        }, 300) // Reduced delay for faster refresh
        return () => clearTimeout(timer)
      }
    }
  }, [pathname, refreshThreads, threads])

  const handleSearch = useCallback(
    async (query: string) => {
      setSearchQuery(query)
      if (!query.trim()) {
        setSearchResults([])
        setIsSearching(false)
        return
      }

      setIsSearching(true)
      try {
        // Search based on current view (archived or active)
        const results = await searchThreads(query, showArchived ? true : false)
        setSearchResults(results)
      } catch (error) {
        console.error("Search failed:", error)
        toast.error("Failed to search conversations")
      } finally {
        setIsSearching(false)
      }
    },
    [searchThreads, showArchived]
  )

  const handleThreadClick = useCallback(
    (threadId: string) => {
      if (onHistoryClick) {
        onHistoryClick(threadId)
      } else {
        router.push(`/conversations/${threadId}`)
      }
    },
    [onHistoryClick, router]
  )

  const handleArchive = useCallback(
    async (threadId: string, archived: boolean) => {
      try {
        await archiveThread(threadId, archived)
        toast.success(archived ? "Conversation archived" : "Conversation unarchived")
        // Refresh threads list
        await refreshThreads()
      } catch (error) {
        toast.error("Failed to archive conversation")
      }
    },
    [archiveThread, refreshThreads]
  )

  const handleDelete = useCallback(
    async (threadId: string) => {
      try {
        await deleteThread(threadId)
        toast.success("Conversation deleted")
        // If deleted thread was current, redirect to new chat
        if (currentThreadId === threadId) {
          router.push("/conversations")
        }
        // Refresh threads list
        await refreshThreads()
      } catch (error) {
        toast.error("Failed to delete conversation")
      }
    },
    [deleteThread, refreshThreads, currentThreadId, router]
  )

  const handleRename = useCallback(
    async (threadId: string, title: string) => {
      try {
        await updateThreadTitle(threadId, title)
        toast.success("Conversation renamed")
        // Refresh threads list
        await refreshThreads()
      } catch (error) {
        toast.error("Failed to rename conversation")
      }
    },
    [updateThreadTitle, refreshThreads]
  )

  const handlePin = useCallback(
    async (threadId: string, pinned: boolean) => {
      try {
        await pinThread(threadId, pinned)
        toast.success(pinned ? "Conversation pinned" : "Conversation unpinned")
        // Refresh threads list
        await refreshThreads()
      } catch (error) {
        toast.error("Failed to pin conversation")
      }
    },
    [pinThread, refreshThreads]
  )

  const handleDeleteAll = useCallback(
    async () => {
      // Show confirmation dialog
      const confirmed = window.confirm(
        "⚠️ WARNING: Delete All Conversations?\n\n" +
        "This will permanently delete ALL your conversations (both active and archived).\n\n" +
        "This action CANNOT be undone and all data will be lost forever.\n\n" +
        "Are you absolutely sure you want to continue?"
      )

      if (!confirmed) {
        return
      }

      // Second confirmation for extra safety
      const doubleConfirmed = window.confirm(
        "🚨 FINAL CONFIRMATION\n\n" +
        `You are about to delete ${threads.length} conversation(s).\n\n` +
        "This is your last chance to cancel.\n\n" +
        "Click OK to DELETE EVERYTHING or Cancel to keep your conversations."
      )

      if (!doubleConfirmed) {
        return
      }

      try {
        await deleteAllThreads()
        toast.success("All conversations deleted")
        // Refresh will show empty state
        await refreshThreads()
      } catch (error) {
        toast.error("Failed to delete all conversations. Some conversations may have been deleted.")
        // Still refresh to show current state
        await refreshThreads()
      }
    },
    [deleteAllThreads, refreshThreads, threads.length]
  )

  // Filter and organize threads
  const organizedThreads = useMemo(() => {
    if (!useNewThreadsSystem) {
      return null // Use legacy history
    }

    // Use search results if searching, otherwise use all threads
    const threadsToShow = searchQuery.trim() ? searchResults : threads

    // Filter threads based on archived view state
    const filteredThreads = showArchived
      ? threadsToShow.filter((t) => t.archived)
      : threadsToShow.filter((t) => !t.archived)

    // Separate pinned and unpinned, sort pinned by updated_at
    const pinned = filteredThreads
      .filter((t) => t.pinned)
      .sort((a, b) => {
        const dateA = new Date(a.updated_at || a.created_at).getTime()
        const dateB = new Date(b.updated_at || b.created_at).getTime()
        return dateB - dateA // Most recent first
      })
    const unpinned = filteredThreads.filter((t) => !t.pinned)

    // Group unpinned by date
    const grouped = groupThreadsByDate(unpinned)

    return {
      pinned,
      grouped,
    }
  }, [threads, searchResults, searchQuery, useNewThreadsSystem, showArchived])

  return (
    <div
      className={cn(
        "h-full bg-black flex flex-col border-r border-zinc-800/50 transition-all duration-300 ease-in-out hidden md:flex",
        isCollapsed ? "w-[60px]" : "w-[260px]",
      )}
    >
      {/* Header */}
      <div className={cn("h-14 flex items-center px-3", isCollapsed ? "justify-center" : "justify-between")}>
        {!isCollapsed && (
          <>
            <div className="flex items-center gap-3 px-2 py-1 rounded-md hover:bg-zinc-900 cursor-pointer transition-colors group">
              <div className="w-10 h-10 flex items-center justify-center relative flex-shrink-0">
                <img
                  src="/syntralogo.png?v=2"
                  alt="SYNTRA AI"
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    console.error('Logo failed to load:', e);
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
              <span className="font-semibold text-zinc-200">Syntra</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="text-zinc-400 hover:text-white hover:bg-zinc-900"
              onClick={() => setIsCollapsed(!isCollapsed)}
            >
              <PanelLeft className="w-5 h-5" />
            </Button>
          </>
        )}
        {isCollapsed && (
          <div className="w-12 h-12 flex items-center justify-center relative cursor-pointer" onClick={() => setIsCollapsed(!isCollapsed)}>
            <img
              src="/syntralogo.png?v=2"
              alt="SYNTRA AI"
              className="w-full h-full object-contain"
              onError={(e) => {
                console.error('Logo failed to load:', e);
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex-1 py-2 px-2 space-y-2 overflow-hidden flex flex-col">
        <Button
          variant="ghost"
          onClick={onNewChat}
          className={cn(
            "w-full justify-start text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 shrink-0",
            isCollapsed && "justify-center px-0",
          )}
        >
          <Plus className="w-5 h-5" />
          {!isCollapsed && <span className="ml-2">New chat</span>}
        </Button>

        {/* History Section - Legacy support */}
        {!isCollapsed && history.length > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
              <Clock className="w-4 h-4" />
              <span>Recent</span>
            </div>
            <div className="space-y-1 max-h-[400px] overflow-y-auto">
              {history.slice(0, 20).map((item) => (
                <div
                  key={item.id}
                  className="group"
                >
                  {renameId === item.id ? (
                    <div className="px-3 py-2 bg-zinc-900 rounded-md flex gap-2">
                      <input
                        type="text"
                        value={renameName}
                        onChange={(e) => setRenameName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRenameSubmit(item.id)
                          if (e.key === 'Escape') {
                            setRenameId(null)
                            setRenameName('')
                          }
                        }}
                        autoFocus
                        className="flex-1 bg-zinc-800 text-zinc-100 text-sm px-2 py-1 rounded border border-zinc-700 focus:outline-none focus:border-green-400"
                        placeholder="Chat name"
                      />
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRenameSubmit(item.id)}
                        className="h-7 w-7 p-0 text-green-400 hover:bg-zinc-800"
                      >
                        ✓
                      </Button>
                    </div>
                  ) : (
                    <div
                      onClick={() => onHistoryClick?.(item.id)}
                      className="w-full text-left px-3 py-2 text-sm text-zinc-300 hover:text-zinc-100 hover:bg-zinc-900 rounded-md transition-colors cursor-pointer flex justify-between items-start"
                    >
                      <div className="flex-1">
                        <div className="truncate">{item.firstLine}</div>
                        <div className="text-xs text-zinc-500 mt-0.5">{item.timestamp}</div>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-zinc-900 border-zinc-800">
                          <DropdownMenuItem
                            onClick={() => {
                              setRenameId(item.id)
                              setRenameName(item.firstLine)
                            }}
                            className="text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 cursor-pointer flex gap-2"
                          >
                            <Edit2 className="w-4 h-4" />
                            <span>Rename</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => onDeleteChat?.(item.id)}
                            className="text-red-400 hover:text-red-300 hover:bg-zinc-800 cursor-pointer flex gap-2"
                          >
                            <Trash2 className="w-4 h-4" />
                            <span>Delete</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Search Bar */}
        {!isCollapsed && useNewThreadsSystem && (
          <div className="shrink-0 px-2">
            <ChatSearch
              onSearch={handleSearch}
              placeholder="Search conversations..."
              className="w-full"
            />
          </div>
        )}

        {/* Archived/Active Toggle */}
        {!isCollapsed && useNewThreadsSystem && (
          <div className="shrink-0 px-2 pt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setShowArchived(!showArchived)
                // Clear search when switching views
                setSearchQuery("")
                setSearchResults([])
              }}
              className={cn(
                "w-full justify-start text-xs hover:bg-zinc-900",
                showArchived ? "text-zinc-100 bg-zinc-900" : "text-zinc-400 hover:text-zinc-100"
              )}
            >
              {showArchived ? (
                <>
                  <Clock className="w-4 h-4 mr-2" />
                  View Active Chats
                </>
              ) : (
                <>
                  <Archive className="w-4 h-4 mr-2" />
                  View Archived
                </>
              )}
            </Button>
          </div>
        )}

        {/* Threads Section */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {!isCollapsed && (
            <>
              {useNewThreadsSystem && organizedThreads ? (
                // New threads system
                <>
                  {isLoading && !searchQuery && (
                    <div className="px-2 py-4 text-center text-sm text-zinc-500">
                      Loading conversations...
                    </div>
                  )}

                  {!isLoading && organizedThreads.pinned.length === 0 &&
                    Object.values(organizedThreads.grouped).every((g) => g.length === 0) &&
                    !searchQuery && (
                      <div className="px-2 py-4 text-center text-sm text-zinc-500">
                        {showArchived
                          ? "No archived conversations"
                          : "No conversations yet. Start a new chat!"}
                      </div>
                    )}

                  {/* Search Results */}
                  {searchQuery.trim() && (
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
                        <Clock className="w-4 h-4" />
                        <span>
                          {isSearching
                            ? "Searching..."
                            : `Search results (${searchResults.length})`}
                        </span>
                      </div>
                      {isSearching ? (
                        <div className="px-2 py-4 text-center text-sm text-zinc-500">
                          Searching...
                        </div>
                      ) : searchResults.length === 0 ? (
                        <div className="px-2 py-4 text-center text-sm text-zinc-500">
                          No conversations found
                        </div>
                      ) : (
                        <div className="space-y-1">
                          {searchResults.map((thread) => (
                            <ThreadItem
                              key={thread.id}
                              thread={thread}
                              isActive={currentThreadId === thread.id}
                              onClick={() => handleThreadClick(thread.id)}
                              onArchive={handleArchive}
                              onDelete={handleDelete}
                              onRename={handleRename}
                              onPin={handlePin}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Pinned Threads */}
                  {!searchQuery && organizedThreads.pinned.length > 0 && (
                    <div className="space-y-1 mb-2">
                      <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
                        <Pin className="w-4 h-4" />
                        <span>Pinned</span>
                      </div>
                      <div className="space-y-1">
                        {organizedThreads.pinned.map((thread) => (
                          <ThreadItem
                            key={thread.id}
                            thread={thread}
                            isActive={currentThreadId === thread.id}
                            onClick={() => handleThreadClick(thread.id)}
                            onArchive={handleArchive}
                            onDelete={handleDelete}
                            onRename={handleRename}
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Date-Grouped Threads */}
                  {!searchQuery &&
                    (organizedThreads.grouped.today.length > 0 ||
                      organizedThreads.grouped.yesterday.length > 0 ||
                      organizedThreads.grouped.thisWeek.length > 0 ||
                      organizedThreads.grouped.thisMonth.length > 0 ||
                      organizedThreads.grouped.older.length > 0) && (
                      <div className="space-y-1">
                        {organizedThreads.grouped.today.length > 0 && (
                          <div className="space-y-1 mb-2">
                            <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
                              <Clock className="w-4 h-4" />
                              <span>{getDateGroupLabel("today")}</span>
                            </div>
                            {organizedThreads.grouped.today.map((thread) => (
                              <ThreadItem
                                key={thread.id}
                                thread={thread}
                                isActive={currentThreadId === thread.id}
                                onClick={() => handleThreadClick(thread.id)}
                                onArchive={handleArchive}
                                onDelete={handleDelete}
                                onRename={handleRename}
                              />
                            ))}
                          </div>
                        )}

                        {organizedThreads.grouped.yesterday.length > 0 && (
                          <div className="space-y-1 mb-2">
                            <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
                              <Clock className="w-4 h-4" />
                              <span>{getDateGroupLabel("yesterday")}</span>
                            </div>
                            {organizedThreads.grouped.yesterday.map((thread) => (
                              <ThreadItem
                                key={thread.id}
                                thread={thread}
                                isActive={currentThreadId === thread.id}
                                onClick={() => handleThreadClick(thread.id)}
                                onArchive={handleArchive}
                                onDelete={handleDelete}
                                onRename={handleRename}
                              />
                            ))}
                          </div>
                        )}

                        {organizedThreads.grouped.thisWeek.length > 0 && (
                          <div className="space-y-1 mb-2">
                            <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
                              <Clock className="w-4 h-4" />
                              <span>{getDateGroupLabel("thisWeek")}</span>
                            </div>
                            {organizedThreads.grouped.thisWeek.map((thread) => (
                              <ThreadItem
                                key={thread.id}
                                thread={thread}
                                isActive={currentThreadId === thread.id}
                                onClick={() => handleThreadClick(thread.id)}
                                onArchive={handleArchive}
                                onDelete={handleDelete}
                                onRename={handleRename}
                              />
                            ))}
                          </div>
                        )}

                        {organizedThreads.grouped.thisMonth.length > 0 && (
                          <div className="space-y-1 mb-2">
                            <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
                              <Clock className="w-4 h-4" />
                              <span>{getDateGroupLabel("thisMonth")}</span>
                            </div>
                            {organizedThreads.grouped.thisMonth.map((thread) => (
                              <ThreadItem
                                key={thread.id}
                                thread={thread}
                                isActive={currentThreadId === thread.id}
                                onClick={() => handleThreadClick(thread.id)}
                                onArchive={handleArchive}
                                onDelete={handleDelete}
                                onRename={handleRename}
                              />
                            ))}
                          </div>
                        )}

                        {organizedThreads.grouped.older.length > 0 && (
                          <div className="space-y-1 mb-2">
                            <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
                              <Clock className="w-4 h-4" />
                              <span>{getDateGroupLabel("older")}</span>
                            </div>
                            {organizedThreads.grouped.older.map((thread) => (
                              <ThreadItem
                                key={thread.id}
                                thread={thread}
                                isActive={currentThreadId === thread.id}
                                onClick={() => handleThreadClick(thread.id)}
                                onArchive={handleArchive}
                                onDelete={handleDelete}
                                onRename={handleRename}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                </>
              ) : (
                // Legacy history system (backward compatibility)
                <>
                  {history.length > 0 && (
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 px-2 py-1 text-xs text-zinc-500 uppercase tracking-wider">
                        <Clock className="w-4 h-4" />
                        <span>Recent</span>
                      </div>
                      <div className="space-y-1">
                        {history.slice(0, 20).map((item) => (
                          <button
                            key={item.id}
                            onClick={() => onHistoryClick?.(item.id)}
                            className="w-full text-left px-3 py-2 text-sm text-zinc-300 hover:text-zinc-100 hover:bg-zinc-900 rounded-md transition-colors group"
                          >
                            <div className="truncate">{item.firstLine}</div>
                            <div className="text-xs text-zinc-500 mt-0.5">{item.timestamp}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="p-2 space-y-2 mt-auto">
        {/* Delete All Button */}
        {!isCollapsed && useNewThreadsSystem && threads.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDeleteAll}
            className="w-full justify-start text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete All Conversations
          </Button>
        )}

        {isCollapsed ? (
          <Button
            variant="ghost"
            size="icon"
            className="w-full h-10 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
          >
            <ExternalLink className="w-5 h-5" />
          </Button>
        ) : (
          <Button className="w-full bg-white text-black hover:bg-zinc-200 justify-center gap-2">
            <ExternalLink className="w-4 h-4" />
            Upgrade
          </Button>
        )}

        {user && clerkUser ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className={cn(
                  "flex items-center gap-3 w-full rounded-lg p-2 hover:bg-zinc-900 cursor-pointer transition-colors",
                  isCollapsed && "justify-center px-0",
                )}
              >
                <Avatar className="h-8 w-8 bg-zinc-800 border border-zinc-700">
                  {clerkUser.profileImageUrl ? (
                    <AvatarImage src={clerkUser.profileImageUrl} alt={user.name || "User"} />
                  ) : null}
                  <AvatarFallback>
                    {user?.name ? user.name.charAt(0).toUpperCase() : user?.email?.charAt(0).toUpperCase() || 'U'}
                  </AvatarFallback>
                </Avatar>
                {!isCollapsed && (
                  <>
                    <div className="flex-1 overflow-hidden text-left">
                      <p className="text-sm font-medium text-zinc-200 truncate">
                        {user?.name || user?.email || 'User'}
                      </p>
                      <p className="text-xs text-zinc-500 truncate">
                        Online
                      </p>
                    </div>
                    <ChevronsUpDown className="w-4 h-4 text-zinc-500" />
                  </>
                )}
              </button>
            </DropdownMenuTrigger>
            {!isCollapsed && (
              <DropdownMenuContent align="end" className="w-56 bg-zinc-900 border-zinc-800">
                <DropdownMenuItem disabled className="flex flex-col items-start py-2">
                  <p className="text-sm font-medium text-zinc-200">{user?.name || 'User'}</p>
                  <p className="text-xs text-zinc-500">{user?.email}</p>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={async () => {
                    try {
                      await signOut()
                    } catch (error) {
                      console.error("Sign out error:", error)
                    }
                  }}
                  className="text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 cursor-pointer flex gap-2"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            )}
          </DropdownMenu>
        ) : (
          <div
            className={cn(
              "flex items-center gap-3 rounded-lg p-2 hover:bg-zinc-900 cursor-pointer transition-colors",
              isCollapsed && "justify-center px-0",
            )}
            onClick={() => {
              router.push('/auth/sign-in')
            }}
          >
            <Avatar className="h-8 w-8 bg-zinc-800 text-zinc-400 border border-zinc-700">
              <AvatarFallback>
                G
              </AvatarFallback>
            </Avatar>
            {!isCollapsed && (
              <>
                <div className="flex-1 overflow-hidden text-left">
                  <p className="text-sm font-medium text-zinc-200 truncate">
                    Guest
                  </p>
                  <p className="text-xs text-zinc-500 truncate">
                    Sign In
                  </p>
                </div>
                <ChevronsUpDown className="w-4 h-4 text-zinc-500" />
              </>
            )}
          </div>
        )}
      </div>
    </div >
  )
}