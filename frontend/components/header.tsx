"use client"

import { ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import Image from "next/image"

export function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-10">
          <a href="/" className="flex items-center gap-2">
            <Image src="/syntra-logo.png" alt="Syntra" width={32} height={32} className="rounded-sm" />
            <span className="text-xl font-semibold text-foreground">Syntra</span>
          </a>

          <nav className="hidden md:flex items-center gap-1">
            <NavDropdown label="Products" />
            <NavDropdown label="Solutions" />
            <a
              href="#pricing"
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </a>
            <NavDropdown label="Learn" />
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" className="text-muted-foreground hover:text-foreground">
            Login
          </Button>
          <Button className="bg-white text-black hover:bg-gray-100 rounded-full px-5">Sign up for free</Button>
        </div>
      </div>
    </header>
  )
}

function NavDropdown({ label }: { label: string }) {
  return (
    <button className="flex items-center gap-1 px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
      {label}
      <ChevronDown className="w-4 h-4" />
    </button>
  )
}
