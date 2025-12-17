import { Button } from "@/components/ui/button"
import { ArrowRight, Brain, CheckCircle2, PenTool, Search, Sparkles, Users } from "lucide-react"
import Image from "next/image"
import Link from "next/link"

const stages = [
  {
    stage: 1,
    name: "Analyst",
    description: "Breaks down your question into clear sub-problems and identifies key constraints",
    icon: Brain,
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/20",
  },
  {
    stage: 2,
    name: "Researcher",
    description: "Gathers and organizes research, facts, and context needed to answer your question",
    icon: Search,
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
    borderColor: "border-purple-500/20",
  },
  {
    stage: 3,
    name: "Creator",
    description: "Drafts comprehensive, well-structured answers based on analysis and research",
    icon: PenTool,
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/20",
  },
  {
    stage: 4,
    name: "Critic",
    description: "Evaluates drafts for correctness, clarity, and identifies areas for improvement",
    icon: CheckCircle2,
    color: "text-orange-400",
    bgColor: "bg-orange-500/10",
    borderColor: "border-orange-500/20",
  },
  {
    stage: 5,
    name: "LLM Council",
    description: "Multi-model council judges and aggregates insights, selecting the best approach",
    icon: Users,
    color: "text-cyan-400",
    bgColor: "bg-cyan-500/10",
    borderColor: "border-cyan-500/20",
  },
  {
    stage: 6,
    name: "Synthesizer",
    description: "Produces the final polished answer that you receive, integrating all insights",
    icon: Sparkles,
    color: "text-pink-400",
    bgColor: "bg-pink-500/10",
    borderColor: "border-pink-500/20",
  },
]

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
          <span key={tag} className="px-2 py-1 text-xs rounded-md bg-muted/30 text-muted-foreground">
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}

export function CollaborationModeSection() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-4">
            Collaboration Mode — Six Minds, One Answer
          </h2>
          <p className="text-muted-foreground max-w-3xl mx-auto text-lg">
            When you enable Collaboration Mode, Syntra orchestrates multiple AI models working together through a
            sophisticated 6-stage pipeline. Each stage uses the best model for that specific task, ensuring you get
            the most accurate, well-researched, and polished answer possible.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {stages.map((stage) => {
            const Icon = stage.icon
            return (
              <div
                key={stage.stage}
                className={`p-6 rounded-xl border ${stage.borderColor} ${stage.bgColor} hover:border-opacity-40 transition-all`}
              >
                <div className="flex items-start gap-4 mb-4">
                  <div className={`p-3 rounded-lg ${stage.bgColor} ${stage.borderColor} border`}>
                    <Icon className={`w-6 h-6 ${stage.color}`} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-muted-foreground">Stage {stage.stage}</span>
                    </div>
                    <h3 className="text-lg font-semibold text-foreground">{stage.name}</h3>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{stage.description}</p>
              </div>
            )
          })}
        </div>

        <div className="bg-gradient-to-br from-primary/10 via-primary/5 to-transparent rounded-2xl border border-primary/20 p-8 md:p-12">
          <div className="max-w-3xl mx-auto text-center">
            <h3 className="text-2xl md:text-3xl font-bold text-foreground mb-4">
              Why Collaboration Mode?
            </h3>
            <p className="text-muted-foreground mb-6 text-lg leading-relaxed">
              Instead of relying on a single AI model, Collaboration Mode leverages the strengths of multiple models
              working together. Each model is dynamically selected for the stage where it performs best, creating a
              more accurate, thorough, and reliable answer than any single model could provide alone.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/conversations">
                <Button size="lg" className="bg-primary hover:bg-primary/90 text-primary-foreground">
                  Try Collaboration Mode
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
              <Link href="/docs">
                <Button size="lg" variant="outline">
                  Learn More
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}




