"use client"

import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuSeparator,
    ContextMenuTrigger,
} from "@/components/ui/context-menu"
import type { Thread } from "@/hooks/use-threads"
import { formatThreadDate } from "@/lib/date-utils"
import { cn } from "@/lib/utils"
import { Archive, ArchiveRestore, Edit2, Pin, PinOff, Trash2 } from "lucide-react"
import { useState } from "react"

interface ThreadItemProps {
    thread: Thread
    isActive?: boolean
    onClick?: () => void
    onArchive?: (threadId: string, archived: boolean) => Promise<void>
    onDelete?: (threadId: string) => Promise<void>
    onRename?: (threadId: string, title: string) => Promise<void>
    onPin?: (threadId: string, pinned: boolean) => Promise<void>
}

export function ThreadItem({
    thread,
    isActive = false,
    onClick,
    onArchive,
    onDelete,
    onRename,
    onPin,
}: ThreadItemProps) {
    const [isEditing, setIsEditing] = useState(false)
    const [editTitle, setEditTitle] = useState(thread.title || "")
    const [isLoading, setIsLoading] = useState(false)

    const handleRename = async () => {
        if (!onRename || editTitle.trim() === thread.title) {
            setIsEditing(false)
            return
        }

        setIsLoading(true)
        try {
            await onRename(thread.id, editTitle.trim())
            setIsEditing(false)
        } catch (error) {
            console.error("Failed to rename thread:", error)
            setEditTitle(thread.title || "")
        } finally {
            setIsLoading(false)
        }
    }

    const handleArchive = async () => {
        if (!onArchive) return
        setIsLoading(true)
        try {
            await onArchive(thread.id, !thread.archived)
        } catch (error) {
            console.error("Failed to archive thread:", error)
        } finally {
            setIsLoading(false)
        }
    }

    const handleDelete = async () => {
        if (!onDelete) return
        if (!confirm("Are you sure you want to delete this conversation? This action cannot be undone.")) {
            return
        }

        setIsLoading(true)
        try {
            await onDelete(thread.id)
        } catch (error) {
            console.error("Failed to delete thread:", error)
        } finally {
            setIsLoading(false)
        }
    }

    const handlePin = async () => {
        if (!onPin) return
        setIsLoading(true)
        try {
            await onPin(thread.id, !thread.pinned)
        } catch (error) {
            console.error("Failed to pin thread:", error)
        } finally {
            setIsLoading(false)
        }
    }

    const displayTitle = thread.title || thread.last_message_preview || "Untitled conversation"
    const timestamp = thread.updated_at || thread.created_at

    return (
        <ContextMenu>
            <ContextMenuTrigger asChild>
                <button
                    onClick={onClick}
                    disabled={isLoading}
                    className={cn(
                        "w-full text-left px-3 py-2 text-sm rounded-md transition-colors group relative",
                        isActive
                            ? "bg-zinc-800 text-zinc-100"
                            : "text-zinc-300 hover:text-zinc-100 hover:bg-zinc-900",
                        isLoading && "opacity-50 cursor-not-allowed"
                    )}
                >
                    <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                            {isEditing ? (
                                <input
                                    type="text"
                                    value={editTitle}
                                    onChange={(e) => setEditTitle(e.target.value)}
                                    onBlur={handleRename}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                            handleRename()
                                        } else if (e.key === "Escape") {
                                            setEditTitle(thread.title || "")
                                            setIsEditing(false)
                                        }
                                    }}
                                    autoFocus
                                    className="w-full bg-zinc-800 text-zinc-100 px-2 py-1 rounded text-sm focus:outline-none focus:ring-1 focus:ring-zinc-600"
                                    onClick={(e) => e.stopPropagation()}
                                />
                            ) : (
                                <div className="flex items-center gap-2">
                                    {thread.pinned && (
                                        <Pin className="w-3 h-3 text-zinc-500 flex-shrink-0" />
                                    )}
                                    <div className="truncate">{displayTitle}</div>
                                </div>
                            )}
                            {!isEditing && thread.last_message_preview && (
                                <div className="text-xs text-zinc-500 mt-0.5 truncate">
                                    {thread.last_message_preview}
                                </div>
                            )}
                            {!isEditing && timestamp && (
                                <div className="text-xs text-zinc-500 mt-0.5">
                                    {formatThreadDate(timestamp)}
                                </div>
                            )}
                        </div>
                    </div>
                </button>
            </ContextMenuTrigger>

            <ContextMenuContent className="w-48 bg-zinc-900 border-zinc-800">
                {onRename && (
                    <ContextMenuItem
                        onClick={(e) => {
                            e.stopPropagation()
                            setIsEditing(true)
                        }}
                        className="text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
                    >
                        <Edit2 className="w-4 h-4 mr-2" />
                        Rename
                    </ContextMenuItem>
                )}

                {onPin && (
                    <ContextMenuItem
                        onClick={(e) => {
                            e.stopPropagation()
                            handlePin()
                        }}
                        className="text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
                    >
                        {thread.pinned ? (
                            <>
                                <PinOff className="w-4 h-4 mr-2" />
                                Unpin
                            </>
                        ) : (
                            <>
                                <Pin className="w-4 h-4 mr-2" />
                                Pin
                            </>
                        )}
                    </ContextMenuItem>
                )}

                {onArchive && (
                    <ContextMenuItem
                        onClick={(e) => {
                            e.stopPropagation()
                            handleArchive()
                        }}
                        className="text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
                    >
                        {thread.archived ? (
                            <>
                                <ArchiveRestore className="w-4 h-4 mr-2" />
                                Unarchive
                            </>
                        ) : (
                            <>
                                <Archive className="w-4 h-4 mr-2" />
                                Archive
                            </>
                        )}
                    </ContextMenuItem>
                )}

                {onDelete && (
                    <>
                        <ContextMenuSeparator className="bg-zinc-800" />
                        <ContextMenuItem
                            onClick={(e) => {
                                e.stopPropagation()
                                handleDelete()
                            }}
                            variant="destructive"
                            className="text-red-400 hover:bg-red-500/10 hover:text-red-300"
                        >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                        </ContextMenuItem>
                    </>
                )}
            </ContextMenuContent>
        </ContextMenu>
    )
}

