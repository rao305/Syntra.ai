"use client"

import { useAuth } from "@/components/auth/auth-provider"
import { Button } from "@/components/ui/button"
import { useUser } from "@clerk/nextjs"
import { ChevronDown, LogOut } from "lucide-react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"

export function Header() {
  const { user, loading, signOut } = useAuth()
  const { user: clerkUser } = useUser()
  const router = useRouter()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const handleSignOut = async () => {
    try {
      await signOut()
    } catch (error) {
      console.error("Sign out error:", error)
    }
  }

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-10">
          <a href="/" className="flex items-center gap-2">
            <Image src="/syntralogo.png" alt="SYNTRA AI" width={32} height={32} className="rounded-sm" />
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
          {loading ? (
            <div className="animate-pulse h-10 w-24 bg-gray-300 rounded-full"></div>
          ) : user && clerkUser ? (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
              >
                {clerkUser.profileImageUrl && (
                  <Image
                    src={clerkUser.profileImageUrl}
                    alt={user.name || "User"}
                    width={32}
                    height={32}
                    className="rounded-full"
                  />
                )}
                <span className="text-sm font-medium text-foreground">{user.name || "User"}</span>
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              </button>

              {showUserMenu && (
                <div className="absolute right-0 top-full mt-2 w-48 bg-background border border-border rounded-lg shadow-lg py-2 z-50">
                  <button
                    onClick={() => {
                      router.push("/conversations")
                      setShowUserMenu(false)
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-foreground hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors"
                  >
                    Go to Chats
                  </button>
                  <button
                    onClick={() => {
                      handleSignOut()
                      setShowUserMenu(false)
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-foreground hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors flex items-center gap-2"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Button
                variant="ghost"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => router.push("/auth/sign-in")}
              >
                Login
              </Button>
              <Button
                className="bg-white text-black hover:bg-gray-100 rounded-full px-5"
                onClick={() => router.push("/auth/sign-up")}
              >
                Sign up for free
              </Button>
            </>
          )}
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
