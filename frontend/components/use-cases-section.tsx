import { ArrowRight } from "lucide-react"

const useCases = [
  {
    title: "Lawyers and Legal Teams",
    description:
      "Draft contracts, summarize case law, and review complex documents by comparing outputs from multiple models. Syntra keeps sensitive legal work encrypted and never trains on your data.",
    image: "/lawyers-legal-team-meeting-office-professional.jpg",
  },
  {
    title: "Doctors & Medical Professionals",
    description:
      "Interpret medical research, summarize clinical notes, and translate complex explanations for patients using multiple models in one private workspace.",
    image: "/doctors-medical-professionals-hospital-healthcare.jpg",
  },
  {
    title: "Financial Advisors & Consultants",
    description:
      "Generate market summaries, analyze reports, and stress-test scenarios by asking different models the same question in a single shared conversation.",
    image: "/financial-advisors-consultants-office-meeting-char.jpg",
  },
  {
    title: "Government Officials & Public Sector",
    description:
      "Prepare briefings, draft policy notes, and analyze long reports with multi-model checks, while keeping data access tightly controlled.",
    image: "/government-officials-public-sector-office-professi.jpg",
  },
]

export function UseCasesSection() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-4">
            Who uses Syntra — And Why?
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Syntra is built for people who want multi-model AI power without giving up privacy or control of their data.
            Every user type gets a workspace tailored to how they think, write, and build.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {useCases.map((useCase, index) => (
            <UseCaseCard key={index} {...useCase} />
          ))}
        </div>
      </div>
    </section>
  )
}

function UseCaseCard({
  title,
  description,
  image,
}: {
  title: string
  description: string
  image: string
}) {
  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden hover:border-muted transition-colors">
      <div className="h-48 overflow-hidden">
        <img src={image || "/placeholder.svg"} alt={title} className="w-full h-full object-cover" />
      </div>
      <div className="p-5">
        <h3 className="text-lg font-semibold text-foreground mb-3">{title}</h3>
        <p className="text-sm text-muted-foreground mb-4 line-clamp-5">{description}</p>
        <a href="#" className="flex items-center gap-1 text-sm text-primary hover:underline">
          Learn more
          <ArrowRight className="w-4 h-4" />
        </a>
      </div>
    </div>
  )
}
