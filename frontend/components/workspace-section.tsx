"use client"

import { ArrowUp, ChevronDown, Paperclip, Search } from "lucide-react"
import Image from "next/image"
import { useEffect, useState } from "react"

type QueryType = {
  text: string
  route: "chatgpt" | "kimi" | "gemini"
}

const queries: QueryType[] = [
  { text: "Write a research paper", route: "chatgpt" },
  { text: "Solve this physics problem", route: "kimi" },
  { text: "Analyze this image", route: "gemini" },
]

export function WorkspaceSection() {
  const [currentQueryIndex, setCurrentQueryIndex] = useState(0)
  const [isRouting, setIsRouting] = useState(false)
  const [activeRoute, setActiveRoute] = useState<"chatgpt" | "kimi" | "gemini" | null>(null)
  const [showCursor, setShowCursor] = useState(false)
  const [cursorClicking, setCursorClicking] = useState(false)

  useEffect(() => {
    // Show query for 2 seconds
    setIsRouting(false)
    setActiveRoute(null)
    setShowCursor(false)
    setCursorClicking(false)

    const showQueryTimeout = setTimeout(() => {
      // Show cursor and animate it to send button
      setShowCursor(true)

      // After cursor reaches button (1s), click it
      const clickTimeout = setTimeout(() => {
        setCursorClicking(true)

        // After click animation (0.3s), start routing
        const routingTimeout = setTimeout(() => {
          setShowCursor(false)
          setCursorClicking(false)
          setIsRouting(true)
          const currentQuery = queries[currentQueryIndex]
          setActiveRoute(currentQuery.route)

          // After routing animation completes (2s), move to next query
          setTimeout(() => {
            setCurrentQueryIndex((prev) => (prev + 1) % queries.length)
          }, 2000)
        }, 300)

        return () => clearTimeout(routingTimeout)
      }, 1000)

      return () => clearTimeout(clickTimeout)
    }, 2000)

    return () => {
      clearTimeout(showQueryTimeout)
    }
  }, [currentQueryIndex])

  const currentQuery = queries[currentQueryIndex]

  return (
    <section className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-4">
            Meet Syntra — Your Multi-Model AI Workspace
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Switch between ChatGPT, Claude, Gemini, and Kimi K2 without losing context. Use the best model for each step
            — all in one shared conversation with unified memory.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row items-center justify-center gap-8">
          <style>{`
            @keyframes moveCursorToButton {
              0% {
                top: 30%;
                left: 20px;
                transform: translate(-50%, -50%);
              }
              100% {
                top: calc(100% - 20px);
                left: calc(100% - 20px);
                transform: translate(-50%, -50%);
              }
            }
            .cursor-animation {
              animation: moveCursorToButton 1s ease-in-out forwards;
            }
          `}</style>
          <div className="w-full max-w-md bg-card rounded-xl border border-border p-4 relative">
            {/* Animated cursor */}
            {showCursor && (
              <div className="absolute z-50 pointer-events-none cursor-animation">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  className={`transition-transform duration-100 ${cursorClicking ? "scale-75" : ""}`}
                >
                  <path
                    d="M3 3L10.07 19.97L12.58 12.58L19.97 10.07L3 3Z"
                    fill="white"
                    stroke="black"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            )}
            <div className="mb-16 min-h-[60px]">
              <p className="text-muted-foreground mb-2">How can I help you today?</p>
              <p
                key={currentQueryIndex}
                className="text-foreground text-lg font-medium animate-in fade-in duration-500"
              >
                {currentQuery.text}
              </p>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button className="p-2 hover:bg-secondary rounded-lg transition-colors">
                  <Paperclip className="w-5 h-5 text-muted-foreground" />
                </button>
                <button className="p-2 hover:bg-secondary rounded-lg transition-colors">
                  <Search className="w-5 h-5 text-muted-foreground" />
                </button>
              </div>

              <div className="flex items-center gap-3 relative">
                <button className="flex items-center gap-2 px-3 py-2 hover:bg-secondary rounded-lg transition-colors">
                  <span className="text-sm text-muted-foreground">Auto · Uses best model</span>
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                </button>
                <button
                  className={`p-2 bg-white rounded-full transition-transform duration-100 ${cursorClicking ? "scale-90" : ""
                    }`}
                >
                  <ArrowUp className="w-5 h-5 text-black" />
                </button>
              </div>
            </div>
          </div>

          <div className="hidden lg:block relative">
            <svg width="80" height="200" viewBox="0 0 80 200" className="overflow-visible">
              <defs>
                <style>
                  {`
                    @keyframes dash {
                      to {
                        stroke-dashoffset: -20;
                      }
                    }
                    .routing-path {
                      stroke-dasharray: 5, 5;
                      animation: dash 0.5s linear infinite;
                    }
                  `}
                </style>
              </defs>
              {/* Top path (ChatGPT) */}
              <path
                d="M0 100 Q40 100 40 30 Q40 0 80 0"
                stroke={activeRoute === "chatgpt" ? "#3b82f6" : "#4a4a4a"}
                strokeWidth={activeRoute === "chatgpt" ? "3" : "2"}
                fill="none"
                className={`transition-all duration-500 ${activeRoute === "chatgpt" ? "routing-path" : ""}`}
              />
              {/* Middle path (Kimi) */}
              <path
                d="M0 100 Q40 100 40 100 Q40 100 80 100"
                stroke={activeRoute === "kimi" ? "#3b82f6" : "#4a4a4a"}
                strokeWidth={activeRoute === "kimi" ? "3" : "2"}
                fill="none"
                className={`transition-all duration-500 ${activeRoute === "kimi" ? "routing-path" : ""}`}
              />
              {/* Bottom path (Gemini) */}
              <path
                d="M0 100 Q40 100 40 170 Q40 200 80 200"
                stroke={activeRoute === "gemini" ? "#3b82f6" : "#4a4a4a"}
                strokeWidth={activeRoute === "gemini" ? "3" : "2"}
                fill="none"
                className={`transition-all duration-500 ${activeRoute === "gemini" ? "routing-path" : ""}`}
              />
              {/* Animated starting point */}
              <circle
                cx="0"
                cy="100"
                r="6"
                fill="#ef4444"
                className={`transition-all duration-300 ${isRouting ? "animate-pulse scale-125" : ""}`}
              />
            </svg>
          </div>

          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-4 mb-2">
              <span className="text-sm text-muted-foreground">Featured Models in Syntra</span>
              <a href="#" className="text-sm text-primary hover:underline">
                View all models ↗
              </a>
            </div>

            <ModelCard
              name="ChatGPT 4.1"
              provider="OpenAI"
              tags={["General", "Coding", "Reasoning"]}
              iconSrc="/images/chatgpt.jpg"
              iconInvert
              active={activeRoute === "chatgpt"}
            />
            <ModelCard
              name="Kimi K2"
              provider="Moonshot"
              tags={["Research", "Analysis", "Long-form"]}
              iconSrc="/images/ld-cvejr8qrqcgsdondvzmjr8enakzrai0yvhg-simosokkjquq1jy4yuh0t1nhfmhn5dfavhmrh-s-v3kx8btwozogqhowwzitt0uye-z50raa9iycn4fduo7lygvks0kr7xton-t6toqjv7003qq.png"
              active={activeRoute === "kimi"}
            />
            <ModelCard
              name="Gemini 2.0"
              provider="Google"
              tags={["Research", "Multimodal", "Summaries"]}
              iconSrc="/images/new-gemini-icon-cover.webp"
              active={activeRoute === "gemini"}
            />
          </div>
        </div>
      </div>
    </section>
  )
}

function ModelCard({
  name,
  provider,
  tags,
  iconSrc,
  iconInvert = false,
  active = false,
}: {
  name: string
  provider: string
  tags: string[]
  iconSrc: string
  iconInvert?: boolean
  active?: boolean
}) {
  const isGemini = name.includes("Gemini")
  const isChatGPT = name.includes("ChatGPT")
  const isKimi = name.includes("Kimi")

  // Determine card styling based on active state and model type
  // Only show special colors when actively routing
  let cardClasses = "border-border bg-card/50 transition-all duration-500"

  if (active) {
    if (isGemini) {
      cardClasses = "border-blue-500 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 shadow-lg shadow-blue-500/20 transition-all duration-500"
    } else if (isChatGPT) {
      cardClasses = "border-green-500 bg-gradient-to-br from-green-500/20 to-emerald-500/20 shadow-lg shadow-green-500/20 transition-all duration-500"
    } else if (isKimi) {
      cardClasses = "border-purple-500 bg-gradient-to-br from-purple-500/20 to-pink-500/20 shadow-lg shadow-purple-500/20 transition-all duration-500"
    }
  }

  const providerColor = active
    ? isGemini
      ? "text-blue-400"
      : isChatGPT
        ? "text-green-400"
        : isKimi
          ? "text-purple-400"
          : "text-primary"
    : "text-primary"

  const iconBg = active
    ? isGemini
      ? "bg-blue-500/30"
      : isChatGPT
        ? "bg-green-500/30"
        : isKimi
          ? "bg-purple-500/30"
          : "bg-secondary"
    : "bg-secondary"

  return (
    <div className={`p-4 rounded-xl border ${cardClasses} min-w-[280px] ${active ? "scale-105" : ""}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="font-semibold text-foreground">{name}</h4>
          <p className={`text-sm ${providerColor}`}>by {provider}</p>
        </div>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden ${iconBg} transition-all duration-500`}>
          <Image
            src={iconSrc || "/placeholder.svg"}
            alt={name}
            width={24}
            height={24}
            className={iconInvert ? "invert" : ""}
          />
        </div>
      </div>
      <p className="text-xs text-muted-foreground mb-2">Best for:</p>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <span key={tag} className="px-2 py-1 text-xs rounded-md bg-muted/30 text-muted-foreground">
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}
