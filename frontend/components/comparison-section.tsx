import { Check, X } from "lucide-react"
import Image from "next/image"

const features = [
  { name: "Encrypted Storage", syntra: "yes", chatgpt: "varies", claude: "varies", gemini: "varies" },
  { name: "Client-Side Key Generation", syntra: "yes", chatgpt: "no", claude: "no", gemini: "no" },
  { name: "Database Breach Protection", syntra: "yes", chatgpt: "varies", claude: "varies", gemini: "varies" },
  { name: "User-Controlled Decryption", syntra: "yes", chatgpt: "no", claude: "no", gemini: "no" },
  {
    name: "Processing (Active Use)",
    syntra: "plaintext",
    chatgpt: "plaintext",
    claude: "plaintext",
    gemini: "plaintext",
  },
  { name: "Multi-Model Access", syntra: "yes", chatgpt: "no", claude: "no", gemini: "no" },
  { name: "Plaintext Database Storage", syntra: "no", chatgpt: "varies", claude: "varies", gemini: "varies" },
]

export function ComparisonSection() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground text-center mb-16">
          True Privacy: Syntra vs Others
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-4 px-4 text-sm font-medium text-muted-foreground uppercase tracking-wide">
                  Feature
                </th>
                <th className="text-center py-4 px-4">
                  <div className="flex items-center justify-center gap-2">
                    <Image src="/syntra-logo.png" alt="Syntra" width={20} height={20} className="rounded-sm" />
                    <span className="text-sm font-medium text-foreground">SYNTRA</span>
                  </div>
                </th>
                <th className="text-center py-4 px-4">
                  <div className="flex items-center justify-center gap-2">
                    <Image
                      src="/images/chatgpt.jpg"
                      alt="ChatGPT"
                      width={20}
                      height={20}
                      className="rounded-sm invert"
                    />
                    <span className="text-sm font-medium text-foreground">CHATGPT</span>
                  </div>
                </th>
                <th className="text-center py-4 px-4">
                  <div className="flex items-center justify-center gap-2">
                    <Image src="/images/claude-ai-symbol.png" alt="Claude" width={20} height={20} />
                    <span className="text-sm font-medium text-foreground">CLAUDE</span>
                  </div>
                </th>
                <th className="text-center py-4 px-4">
                  <div className="flex items-center justify-center gap-2 px-3 py-2 bg-blue-500/10 rounded-lg">
                    <Image src="/images/new-gemini-icon-cover.webp" alt="Gemini" width={20} height={20} />
                    <span className="text-sm font-bold text-blue-400">GEMINI</span>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {features.map((feature, index) => (
                <tr key={index} className="border-b border-border hover:bg-white/5 transition-colors">
                  <td className="py-4 px-4 text-sm text-foreground">{feature.name}</td>
                  <td className="py-4 px-4 text-center">
                    <StatusBadge status={feature.syntra} />
                  </td>
                  <td className="py-4 px-4 text-center">
                    <StatusBadge status={feature.chatgpt} />
                  </td>
                  <td className="py-4 px-4 text-center">
                    <StatusBadge status={feature.claude} />
                  </td>
                  <td className="py-4 px-4 text-center bg-blue-500/5">
                    <StatusBadge status={feature.gemini} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

function StatusBadge({ status }: { status: string }) {
  if (status === "yes") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-accent/20 text-accent text-xs rounded-md">
        <Check className="w-3 h-3" /> Yes
      </span>
    )
  }
  if (status === "no") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary/20 text-primary text-xs rounded-md">
        <X className="w-3 h-3" /> No
      </span>
    )
  }
  if (status === "varies") {
    return <span className="inline-flex items-center px-2 py-1 bg-blue-500/20 text-blue-300 text-xs rounded-md font-medium">Varies by plan</span>
  }
  if (status === "plaintext") {
    return <span className="inline-flex items-center px-2 py-1 bg-cyan-500/20 text-cyan-300 text-xs rounded-md font-medium">Plaintext</span>
  }
  return null
}
