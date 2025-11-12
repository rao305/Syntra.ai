"use client"

import { useState } from "react"
import Link from "next/link"
import { Menu, X } from "lucide-react"
import { Button } from "@/components/ui/button"

export function Header() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 font-bold text-xl">
            <div className="w-8 h-8 bg-accent rounded-sm flex items-center justify-center">
              <span className="text-primary font-bold">D</span>
            </div>
            <span className="text-foreground">DAC</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            <Link href="/product" className="text-sm text-muted-foreground hover:text-foreground transition-colors hover:text-emerald-400">
              Product
            </Link>
            <Link href="/use-cases" className="text-sm text-muted-foreground hover:text-foreground transition-colors hover:text-emerald-400">
              Use Cases
            </Link>
            <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors hover:text-emerald-400">
              Pricing
            </Link>
            <Link href="/docs" className="text-sm text-muted-foreground hover:text-foreground transition-colors hover:text-emerald-400">
              Docs
            </Link>
          </nav>

          <div className="hidden md:flex items-center gap-4">
            <Link href="/settings">
              <Button variant="ghost" size="sm">
                Settings
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/">
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                Start Chat
              </Button>
            </Link>
          </div>

          {/* Mobile Menu */}
          <button onClick={() => setIsOpen(!isOpen)} className="md:hidden p-2 rounded-lg hover:bg-muted">
            {isOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

          {/* Mobile Navigation */}
          {isOpen && (
            <nav className="md:hidden pb-4 space-y-2">
              <Link href="/product" className="block px-4 py-2 rounded-lg hover:bg-muted text-sm">
                Product
              </Link>
              <Link href="/use-cases" className="block px-4 py-2 rounded-lg hover:bg-muted text-sm">
                Use Cases
              </Link>
              <Link href="/pricing" className="block px-4 py-2 rounded-lg hover:bg-muted text-sm">
                Pricing
              </Link>
              <Link href="/docs" className="block px-4 py-2 rounded-lg hover:bg-muted text-sm">
                Docs
              </Link>
            <div className="space-y-2 pt-2">
              <Link href="/settings" className="block">
                <Button variant="ghost" size="sm" className="w-full">
                  Settings
                </Button>
              </Link>
              <Link href="/login" className="block">
                <Button variant="ghost" size="sm" className="w-full">
                  Sign In
                </Button>
              </Link>
              <Link href="/" className="block">
                <Button size="sm" className="w-full bg-emerald-600 hover:bg-emerald-700 text-white">
                  Start Chat
                </Button>
              </Link>
            </div>
          </nav>
        )}
      </div>
    </header>
  )
}
