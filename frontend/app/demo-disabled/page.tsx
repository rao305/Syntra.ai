import { ChatInterface } from "@/components/chat-interface"
import { Footer } from "@/components/footer"

export default function DemoPage() {
  return (
    <>
      <main className="min-h-screen pt-24 pb-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-8">
            <div className="text-center space-y-4">
              <h1 className="text-4xl md:text-5xl font-bold text-foreground text-balance">Try Syntra in Action</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Chat with our AI agent to explore capabilities, ask questions, and see the platform in action
              </p>
            </div>

            <div className="grid lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2 h-[600px]">
                <ChatInterface />
              </div>

              <div className="space-y-6">
                <div className="bg-card border border-border rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-foreground mb-3">Getting Started</h3>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• Ask about our features</li>
                    <li>• Explore use cases</li>
                    <li>• Learn about pricing</li>
                    <li>• Discuss security</li>
                  </ul>
                </div>

                <div className="bg-accent/10 border border-accent/20 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-accent mb-2">Pro Tip</h3>
                  <p className="text-sm text-muted-foreground">
                    Try typing keywords like "customer", "sales", "security", or "pricing" to get specific answers.
                  </p>
                </div>

                <div className="bg-card border border-border rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-foreground mb-3">Key Features</h3>
                  <ul className="space-y-2 text-sm">
                    <li className="flex items-start gap-2">
                      <span className="text-accent">✓</span>
                      <span className="text-muted-foreground">Real-time responses</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-accent">✓</span>
                      <span className="text-muted-foreground">Copy messages</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-accent">✓</span>
                      <span className="text-muted-foreground">Smart routing</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
