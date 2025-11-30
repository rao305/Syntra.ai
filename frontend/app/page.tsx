export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6">
            Syntra
          </h1>
          <p className="text-xl md:text-2xl text-slate-300 mb-8 max-w-2xl mx-auto">
            Intelligent LLM Routing Platform
          </p>
          <p className="text-lg text-slate-400 mb-12 max-w-3xl mx-auto">
            Enterprise AI routing platform with intelligent provider selection, unified context, and enterprise-grade security.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16">
            <div className="bg-slate-800 p-8 rounded-lg">
              <h3 className="text-xl font-semibold mb-4">Smart Routing</h3>
              <p className="text-slate-400">Automatically select the best LLM for each request</p>
            </div>
            <div className="bg-slate-800 p-8 rounded-lg">
              <h3 className="text-xl font-semibold mb-4">Multi-Model</h3>
              <p className="text-slate-400">Support for OpenAI, Google, Anthropic, and more</p>
            </div>
            <div className="bg-slate-800 p-8 rounded-lg">
              <h3 className="text-xl font-semibold mb-4">Enterprise Ready</h3>
              <p className="text-slate-400">Built for scale with security and reliability</p>
            </div>
          </div>

          <div className="mt-16">
            <a
              href="/conversations"
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-lg transition"
            >
              Get Started
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}
