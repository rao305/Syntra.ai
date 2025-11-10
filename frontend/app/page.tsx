import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-24">
      <div className="max-w-5xl w-full text-center">
        <h1 className="text-6xl font-bold mb-8">
          Cross-LLM Thread Hub
        </h1>
        <p className="text-xl text-gray-600 mb-12">
          Multi-tenant B2B SaaS for cross-provider LLM threading with governed memory
        </p>

        <div className="flex gap-4 justify-center">
          <Link
            href="/auth/signin"
            className="px-6 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700 font-medium"
          >
            Sign In
          </Link>
          <Link
            href="/threads"
            className="px-6 py-3 bg-gray-200 text-gray-900 rounded-md hover:bg-gray-300 font-medium"
          >
            View Threads
          </Link>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
          <div className="p-6 bg-white rounded-lg shadow">
            <h3 className="font-bold text-lg mb-2">Cross-Provider Threading</h3>
            <p className="text-gray-600 text-sm">
              Start with Perplexity, forward to OpenAI, continue in Gemini - all with preserved context
            </p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow">
            <h3 className="font-bold text-lg mb-2">Governed Memory</h3>
            <p className="text-gray-600 text-sm">
              Private/shared tiers with immutable provenance and dynamic access graphs
            </p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow">
            <h3 className="font-bold text-lg mb-2">Full Audit Trail</h3>
            <p className="text-gray-600 text-sm">
              Every routing decision, memory access, and token usage tracked with hashes
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
