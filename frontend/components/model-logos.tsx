import Image from "next/image"

export function ModelLogos() {
  return (
    <section className="pt-0 pb-12 px-6">
      <p className="text-center text-sm text-muted-foreground mb-8">Powered by the best AI models in the ecosystem</p>

      <div className="flex items-center justify-center gap-12 flex-wrap max-w-4xl mx-auto">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Image src="/images/chatgpt.jpg" alt="ChatGPT" width={24} height={24} className="rounded-sm invert" />
          <span className="text-lg font-medium">ChatGPT</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Image src="/images/claude-ai-symbol.png" alt="Claude" width={24} height={24} />
          <span className="text-lg font-medium">Claude</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Image src="/images/gemini-img.webp" alt="Gemini" width={32} height={32} className="object-cover" />
          <span className="text-lg font-medium">Gemini</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Image
            src="/images/ld-cvejr8qrqcgsdondvzmjr8enakzrai0yvhg-simosokkjquq1jy4yuh0t1nhfmhn5dfavhmrh-s-v3kx8btwozogqhowwzitt0uye-z50raa9iycn4fduo7lygvks0kr7xton-t6toqjv7003qq.png"
            alt="Kimi K2"
            width={24}
            height={24}
            className="rounded-sm"
          />
          <span className="text-lg font-medium">Kimi K2</span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Image src="/images/grok-v2.jpg" alt="Grok" width={24} height={24} className="rounded-sm invert" />
          <span className="text-lg font-medium">Grok</span>
        </div>
      </div>
    </section>
  )
}
