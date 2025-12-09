"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { Search, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"

interface ChatSearchProps {
    onSearch: (query: string) => void
    placeholder?: string
    debounceMs?: number
    className?: string
}

export function ChatSearch({
    onSearch,
    placeholder = "Search conversations...",
    debounceMs = 300,
    className,
}: ChatSearchProps) {
    const [query, setQuery] = useState("")
    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)

    useEffect(() => {
        // Clear previous timer
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current)
        }

        // Set new timer
        if (query.trim()) {
            debounceTimerRef.current = setTimeout(() => {
                onSearch(query.trim())
            }, debounceMs)
        } else {
            onSearch("")
        }

        // Cleanup
        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current)
            }
        }
    }, [query, onSearch, debounceMs])

    const handleClear = () => {
        setQuery("")
        onSearch("")
    }

    return (
        <div className={cn("relative", className)}>
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 pointer-events-none" />
            <Input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={placeholder}
                className={cn(
                    "pl-9 pr-9 h-9 bg-zinc-900/50 border-zinc-800 text-zinc-100 placeholder:text-zinc-500",
                    "focus:bg-zinc-900 focus:border-zinc-700 focus:ring-1 focus:ring-zinc-700"
                )}
            />
            {query && (
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleClear}
                    className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
                >
                    <X className="w-4 h-4" />
                </Button>
            )}
        </div>
    )
}

