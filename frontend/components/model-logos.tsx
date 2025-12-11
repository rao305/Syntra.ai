"use client"

import Image from "next/image"
import { useEffect, useState } from "react"

export function ModelLogos() {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(true)
  }, [])

  const models = [
    { name: "ChatGPT", src: "/images/chatgpt.jpg", className: "rounded-sm invert grayscale", delay: 0 },
    { name: "Claude", src: "/images/claude-ai-symbol.png", className: "grayscale", delay: 100 },
    { name: "Gemini", src: "/images/gemini-img.webp", className: "object-cover grayscale", delay: 200, size: 32 },
    { name: "Kimi K2", src: "/images/ld-cvejr8qrqcgsdondvzmjr8enakzrai0yvhg-simosokkjquq1jy4yuh0t1nhfmhn5dfavhmrh-s-v3kx8btwozogqhowwzitt0uye-z50raa9iycn4fduo7lygvks0kr7xton-t6toqjv7003qq.png", className: "rounded-sm grayscale", delay: 300 },
    { name: "Grok", src: "/images/grok-v2.jpg", className: "rounded-sm invert grayscale", delay: 400 },
  ]

  return (
    <section className="pt-0 pb-12 px-6">
      <p className="text-center text-sm text-muted-foreground mb-8 animate-in fade-in duration-1000">
        Powered by the best AI models in the ecosystem
      </p>

      <div className="flex items-center justify-center gap-12 flex-wrap max-w-4xl mx-auto">
        {models.map((model, index) => (
          <div
            key={model.name}
            className="flex items-center gap-2 text-muted-foreground group cursor-pointer transition-all duration-300 hover:scale-110 hover:text-foreground"
            style={{
              animation: isVisible ? `fadeInUp 0.6s ease-out ${model.delay}ms both` : 'none',
            }}
          >
            <div className="relative">
              <Image
                src={model.src}
                alt={model.name}
                width={model.size || 24}
                height={model.size || 24}
                className={`${model.className} transition-all duration-300 group-hover:grayscale-0 group-hover:scale-110`}
              />
              <div className="absolute inset-0 bg-primary/20 rounded-full blur-md opacity-0 group-hover:opacity-100 transition-opacity duration-300 -z-10"></div>
            </div>
            <span className="text-lg font-medium transition-all duration-300">{model.name}</span>
          </div>
        ))}
      </div>

      <style jsx>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </section>
  )
}
