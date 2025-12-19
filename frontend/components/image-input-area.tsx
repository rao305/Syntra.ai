"use client"

import { SYNTRA_MODELS } from "@/components/syntra-model-selector"
import {
  ArrowUp,
  Brain,
  ChevronDown,
  Code,
  Eye,
  ImageIcon,
  Lock,
  MessageSquare,
  Paperclip,
  Search,
  Upload,
  X,
  Zap,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

interface ImageFile {
  file: File
  url: string
  id: string
}

interface ImageInputAreaProps {
  onSendMessage: (content: string, images?: ImageFile[]) => void
  selectedModel: string
  onModelSelect: (modelId: string) => void
  isLoading?: boolean
  autoRoutedModel?: string | null
  showActionButtons?: boolean
  orgId?: string
  currentThreadId?: string | null
  onCollaborate?: (query: string, orgId: string) => void
}

export function ImageInputArea({
  onSendMessage,
  selectedModel,
  onModelSelect,
  isLoading = false,
  autoRoutedModel,
  showActionButtons = true,
  orgId,
  currentThreadId,
  onCollaborate
}: ImageInputAreaProps) {
  const [isModelOpen, setIsModelOpen] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [images, setImages] = useState<ImageFile[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [isCollaborationMode, setIsCollaborationMode] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const selectedModelData = SYNTRA_MODELS.find(m => m.id === selectedModel) || SYNTRA_MODELS[0]

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsModelOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [])

  // Handle paste events for images
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return

      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile()
          if (file) {
            handleImageFile(file)
          }
        }
      }
    }

    document.addEventListener('paste', handlePaste)
    return () => document.removeEventListener('paste', handlePaste)
  }, [])

  const handleImageFile = (file: File) => {
    if (!file.type.startsWith('image/')) return

    const reader = new FileReader()
    reader.onload = (e) => {
      const imageFile: ImageFile = {
        file,
        url: e.target?.result as string,
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9)
      }
      setImages(prev => [...prev, imageFile])
    }
    reader.readAsDataURL(file)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      if (file.type.startsWith('image/')) {
        handleImageFile(file)
      }
    })

    // Clear the input so the same file can be selected again
    e.target.value = ''
  }

  const removeImage = (id: string) => {
    setImages(prev => prev.filter(img => img.id !== id))
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const files = e.dataTransfer.files
    Array.from(files).forEach(file => {
      if (file.type.startsWith('image/')) {
        handleImageFile(file)
      }
    })
  }

  const handleSend = () => {
    if ((!inputValue.trim() && images.length === 0) || isLoading) {
      return
    }

    const trimmedInput = inputValue.trim()

    // If collaboration mode is active, trigger collaboration instead of normal send
    if (isCollaborationMode && onCollaborate && orgId) {
      console.log('🤝 Sending in Collaboration Mode:', trimmedInput)
      onCollaborate(trimmedInput, orgId)
      setInputValue('')
      setImages([])
      setIsCollaborationMode(false) // Reset collaboration mode after sending
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
      return
    }

    // Normal send
    onSendMessage(trimmedInput, images.length > 0 ? images : undefined)
    setInputValue('')
    setImages([])

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const toggleCollaborationMode = () => {
    setIsCollaborationMode(!isCollaborationMode)
    console.log('🔄 Collaboration mode:', !isCollaborationMode ? 'ENABLED' : 'DISABLED')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value)
    // Auto-resize textarea
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'
  }

  const handleModelSelect = (modelId: string) => {
    onModelSelect(modelId)
    setIsModelOpen(false)
    setSearchQuery('')
  }

  const filteredModels = SYNTRA_MODELS.filter(model =>
    model.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (model.description && model.description.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const codingModels = filteredModels.filter(model =>
    model.features?.some(feature =>
      feature.toLowerCase().includes('code') || feature.toLowerCase().includes('coding')
    )
  )

  return (
    <div className="relative group w-full">
      {/* Suggestion Chips - Above Input (only show on first message) */}
      {showActionButtons && (
        <div className="flex flex-wrap gap-3 mb-6 justify-center items-center">
          <button className="px-4 py-2 rounded-full bg-white/5 backdrop-blur-md border border-white/10 hover:bg-white/10 transition-all text-sm text-zinc-300 hover:text-zinc-100 font-medium">
            💡 Analyze Data
          </button>
          <button className="px-4 py-2 rounded-full bg-white/5 backdrop-blur-md border border-white/10 hover:bg-white/10 transition-all text-sm text-zinc-300 hover:text-zinc-100 font-medium">
            💻 Write Code
          </button>
          <button className="px-4 py-2 rounded-full bg-white/5 backdrop-blur-md border border-white/10 hover:bg-white/10 transition-all text-sm text-zinc-300 hover:text-zinc-100 font-medium">
            ✨ Brainstorm Ideas
          </button>
        </div>
      )}

      {/* Main Input Container with Glow */}
      <div className="relative">
        {/* Glow Effect Background */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-500/0 via-blue-500/10 to-purple-500/0 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

        {/* Main Input Container */}
        <div
          className={cn(
            "relative bg-gradient-to-b from-zinc-800/50 to-zinc-900/50 border rounded-2xl p-3 backdrop-blur-sm transition-all duration-200 shadow-2xl",
            isDragOver && 'border-blue-400/50 bg-blue-950/30',
            isCollaborationMode 
              ? 'border-purple-500/50 shadow-purple-500/20 ring-1 ring-purple-500/30' 
              : 'border-zinc-700/50 shadow-blue-500/0 group-hover:shadow-blue-500/10'
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
        {/* Collaboration Mode Banner */}
        {isCollaborationMode && (
          <div className="mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-purple-500/20 to-blue-500/20 border border-purple-500/30">
            <Zap className="w-4 h-4 text-purple-400 animate-pulse" />
            <span className="text-sm text-purple-200 font-medium">
              Council Collaboration Mode Active
            </span>
            <span className="text-xs text-purple-300/70 ml-auto">
              Press Enter or Send to start orchestration
            </span>
          </div>
        )}
        {/* Image Preview Area */}
        {images.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {images.map((image) => (
              <div key={image.id} className="relative group/image">
                <img
                  src={image.url}
                  alt="Uploaded"
                  className="w-20 h-20 object-cover rounded-lg border border-zinc-700"
                />
                <button
                  onClick={() => removeImage(image.id)}
                  className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover/image:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Drag Overlay */}
        {isDragOver && (
          <div className="absolute inset-0 bg-blue-500/10 border-2 border-dashed border-blue-400 rounded-xl flex items-center justify-center z-10">
            <div className="text-center">
              <Upload className="w-8 h-8 text-blue-400 mx-auto mb-2" />
              <p className="text-blue-400 font-medium">Drop images here</p>
            </div>
          </div>
        )}

        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={handleTextareaChange}
          onKeyDown={handleKeyDown}
          className="w-full bg-transparent text-white placeholder:text-zinc-500 resize-none outline-none min-h-[44px] text-base px-2 py-1 font-medium"
          placeholder={images.length > 0 ? "Ask me about these images..." : "How can I help you today? You can paste or drag images here!"}
          disabled={isLoading}
        />

        <div className="flex items-center justify-between mt-2 pt-2 border-t border-zinc-700/30">
          <div className="flex items-center gap-2">
            {/* File Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 text-zinc-500 hover:text-zinc-300 hover:bg-white/5 rounded-lg transition-colors"
              title="Attach file"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            {/* Image Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 text-zinc-500 hover:text-zinc-300 hover:bg-white/5 rounded-lg transition-colors"
              title="Upload image"
            >
              <ImageIcon className="w-4 h-4" />
            </button>

            <div className="h-6 w-px bg-zinc-800 mx-1" />

            {/* Collaboration Mode Toggle Button */}
            {orgId && onCollaborate && (
              <button
                onClick={toggleCollaborationMode}
                disabled={isLoading}
                title={isCollaborationMode ? "Collaboration mode enabled - Send to start orchestration" : "Enable Council Collaboration mode"}
                className={cn(
                  'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg font-medium text-sm transition-all',
                  isCollaborationMode
                    ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg shadow-purple-500/25 ring-2 ring-purple-400/50'
                    : 'bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 hover:text-zinc-100',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                <Zap className={cn("w-4 h-4", isCollaborationMode && "animate-pulse")} />
                <span>{isCollaborationMode ? 'Collaborate ✓' : 'Collaborate'}</span>
              </button>
            )}

            {/* Hidden File Input */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>

          <div className="flex items-center gap-2">
            <div className="relative" ref={dropdownRef}>
              {isModelOpen && (
                <div className="absolute bottom-full right-0 mb-2 w-[280px] overflow-hidden rounded-xl border border-zinc-700 bg-zinc-900 shadow-2xl animate-in fade-in zoom-in-95 duration-100">
                  <div className="p-2">
                    <div className="relative mb-2">
                      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-500" />
                      <input
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full rounded-lg border border-zinc-800 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-zinc-700 focus:outline-none"
                        placeholder="Search models..."
                      />
                    </div>

                    <div className="space-y-0.5">
                      <div className="flex items-center justify-between rounded-lg px-2 py-2 text-sm text-zinc-400 hover:bg-zinc-800/50 cursor-not-allowed opacity-70">
                        <div className="flex items-center gap-2">
                          <div className="flex h-5 w-5 items-center justify-center">
                            <span className="text-xs">✨</span>
                          </div>
                          <span>Auto</span>
                        </div>
                        <Lock className="h-3.5 w-3.5" />
                      </div>

                      {filteredModels.map((model) => {
                        const Icon = model.icon || MessageSquare
                        const isSelected = model.id === selectedModel

                        return (
                          <div
                            key={model.id}
                            onClick={() => handleModelSelect(model.id)}
                            className={`flex items-center justify-between rounded-lg px-2 py-2 text-sm cursor-pointer transition-colors ${isSelected
                              ? "bg-zinc-800 text-zinc-100"
                              : "text-zinc-300 hover:bg-zinc-800"
                              }`}
                          >
                            <div className="flex items-center gap-2">
                              <div className="flex h-5 w-5 items-center justify-center">
                                <Icon className="h-4 w-4" />
                              </div>
                              <span>{model.name}</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-zinc-400">
                              {model.features?.includes('Chain of thought') && (
                                <Brain className="h-3.5 w-3.5" />
                              )}
                              <Eye className="h-3.5 w-3.5" />
                            </div>
                          </div>
                        )
                      })}
                    </div>

                    {codingModels.length > 0 && (
                      <div className="mt-1 border-t border-zinc-800 pt-1">
                        <div className="flex items-center justify-between rounded-lg px-2 py-2 text-sm text-zinc-400 hover:bg-zinc-800 cursor-pointer">
                          <div className="flex items-center gap-2">
                            <ChevronDown className="h-3.5 w-3.5 -rotate-90" />
                            <Code className="h-4 w-4" />
                            <span>Coding</span>
                          </div>
                          <span className="text-xs">{codingModels.length}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-zinc-800 bg-zinc-900/50 p-1">
                    <div className="grid grid-cols-2 gap-1 rounded-lg bg-zinc-950 p-1">
                      <button className="flex items-center justify-center gap-2 rounded-md bg-white py-1.5 text-xs font-medium text-black shadow-sm">
                        <MessageSquare className="h-3.5 w-3.5" />
                        Chat
                      </button>
                      <button className="flex items-center justify-center gap-2 rounded-md py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200">
                        <ImageIcon className="h-3.5 w-3.5" />
                        Image
                      </button>
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={() => setIsModelOpen(!isModelOpen)}
                className="flex items-center gap-2 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-zinc-300 hover:text-zinc-100 transition-all backdrop-blur-sm relative"
              >
                <span className="font-medium">{selectedModel === 'auto' && autoRoutedModel ? autoRoutedModel : selectedModelData.name}</span>
                <ChevronDown className="w-3 h-3" />
              </button>
            </div>

            <button
              onClick={handleSend}
              disabled={(!inputValue.trim() && images.length === 0) || isLoading}
              className={cn(
                "p-2.5 text-white rounded-lg transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                isCollaborationMode
                  ? "bg-gradient-to-br from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 hover:shadow-purple-500/50"
                  : "bg-gradient-to-br from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 hover:shadow-blue-500/50"
              )}
              title={isCollaborationMode ? "Start Council Orchestration (Enter)" : "Send message (Enter)"}
            >
              {isCollaborationMode ? <Zap className="w-4 h-4" /> : <ArrowUp className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Image Count Indicator */}
        {images.length > 0 && (
          <div className="absolute top-3 right-3 bg-blue-500 text-white text-xs px-2.5 py-1 rounded-full font-medium">
            {images.length} image{images.length > 1 ? 's' : ''}
          </div>
        )}
        </div>
      </div>
    </div>
  )
}