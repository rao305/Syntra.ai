import { Paperclip, Search, ChevronDown, ArrowUp } from "lucide-react"
import Image from "next/image"

export function WorkspaceSection() {
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
          <div className="w-full max-w-md bg-card rounded-xl border border-border p-4">
            <div className="mb-16">
              <p className="text-muted-foreground">How can I help you today?</p>
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

              <div className="flex items-center gap-3">
                <button className="flex items-center gap-2 px-3 py-2 hover:bg-secondary rounded-lg transition-colors">
                  <span className="text-sm text-muted-foreground">Auto · Uses best model</span>
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                </button>
                <button className="p-2 bg-white rounded-full">
                  <ArrowUp className="w-5 h-5 text-black" />
                </button>
              </div>
            </div>
          </div>

          <div className="hidden lg:block relative">
            <svg width="80" height="200" viewBox="0 0 80 200">
              <path d="M0 100 Q40 100 40 30 Q40 0 80 0" stroke="#4a4a4a" strokeWidth="2" fill="none" />
              <path d="M0 100 Q40 100 40 100 Q40 100 80 100" stroke="#4a4a4a" strokeWidth="2" fill="none" />
              <path d="M0 100 Q40 100 40 170 Q40 200 80 200" stroke="#4a4a4a" strokeWidth="2" fill="none" />
              <circle cx="0" cy="100" r="6" fill="#ef4444" />
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
            />
            <ModelCard
              name="Kimi K2"
              provider="Moonshot"
              tags={["Research", "Analysis", "Long-form"]}
              iconSrc="/images/ld-cvejr8qrqcgsdondvzmjr8enakzrai0yvhg-simosokkjquq1jy4yuh0t1nhfmhn5dfavhmrh-s-v3kx8btwozogqhowwzitt0uye-z50raa9iycn4fduo7lygvks0kr7xton-t6toqjv7003qq.png"
            />
            <ModelCard
              name="Gemini 2.0"
              provider="Google"
              tags={["Research", "Multimodal", "Summaries"]}
              iconSrc="/images/new-gemini-icon-cover.webp"
              selected
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
  selected = false,
}: {
  name: string
  provider: string
  tags: string[]
  iconSrc: string
  iconInvert?: boolean
  selected?: boolean
}) {
  const isGemini = name.includes("Gemini")
  const cardClasses = isGemini
    ? "border-blue-500/60 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 hover:border-blue-400/80 hover:from-blue-500/15 hover:to-cyan-500/15 transition-all"
    : selected
    ? "border-primary bg-card"
    : "border-border bg-card/50"

  return (
    <div className={`p-4 rounded-xl border ${cardClasses} min-w-[280px]`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="font-semibold text-foreground">{name}</h4>
          <p className={`text-sm ${isGemini ? "text-blue-400" : "text-primary"}`}>by {provider}</p>
        </div>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden ${isGemini ? "bg-blue-500/20" : "bg-secondary"}`}>
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
          <span key={tag} className={`px-2 py-1 text-xs rounded-md ${isGemini ? "bg-blue-500/20 text-blue-300" : "bg-accent/20 text-accent"}`}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}
