"use client"

import { Clock, PanelLeft, ExternalLink, Plus, ChevronsUpDown, MoreVertical, Trash2, Edit2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import * as React from "react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface SidebarProps {
  isCollapsed: boolean
  setIsCollapsed: (collapsed: boolean) => void
  history?: ChatHistoryItem[]
  onNewChat?: () => void
  onHistoryClick?: (id: string) => void
  onDeleteChat?: (id: string) => void
  onRenameChat?: (id: string, newName: string) => void
  user?: any
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
  user
}: SidebarProps) {
  const [renameId, setRenameId] = React.useState<string | null>(null)
  const [renameName, setRenameName] = React.useState('')

  const handleRenameSubmit = (id: string) => {
    if (renameName.trim()) {
      onRenameChat?.(id, renameName.trim())
      setRenameId(null)
      setRenameName('')
    }
  }

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
          <div className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-zinc-900 cursor-pointer transition-colors group">
            <div className="w-6 h-6 rounded-full bg-zinc-800 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full border-2 border-white/80" />
            </div>
            <span className="font-semibold text-zinc-200">Syntra</span>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="text-zinc-400 hover:text-white hover:bg-zinc-900"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          <PanelLeft className="w-5 h-5" />
        </Button>
      </div>

      {/* Navigation */}
      <div className="flex-1 py-2 px-2 space-y-2">
        <Button
          variant="ghost"
          onClick={onNewChat}
          className={cn(
            "w-full justify-start text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900",
            isCollapsed && "justify-center px-0",
          )}
        >
          <Plus className="w-5 h-5" />
          {!isCollapsed && <span className="ml-2">New chat</span>}
        </Button>

        {/* History Section */}
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
      </div>

      {/* Footer */}
      <div className="p-2 space-y-2 mt-auto">
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

        <div
          className={cn(
            "flex items-center gap-3 rounded-lg p-2 hover:bg-zinc-900 cursor-pointer transition-colors",
            isCollapsed && "justify-center px-0",
          )}
        >
          <Avatar className="h-8 w-8 bg-zinc-800 text-zinc-400 border border-zinc-700">
            <AvatarFallback>
              {user?.email ? user.email.charAt(0).toUpperCase() : 'G'}
            </AvatarFallback>
          </Avatar>
          {!isCollapsed && (
            <>
              <div className="flex-1 overflow-hidden text-left">
                <p className="text-sm font-medium text-zinc-200 truncate">
                  {user?.email || 'Guest'}
                </p>
                <p className="text-xs text-zinc-500 truncate">
                  {user ? 'Online' : 'Sign In'}
                </p>
              </div>
              <ChevronsUpDown className="w-4 h-4 text-zinc-500" />
            </>
          )}
        </div>
      </div>
    </div>
  )
}