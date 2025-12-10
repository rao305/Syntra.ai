"use client";

import { API_BASE_URL } from "@/lib/api";
import { clearSession, saveSession, getStoredSession } from "@/lib/session";
import { useAuth as useClerkAuth, useUser } from "@clerk/nextjs";
import { useRouter, usePathname } from "next/navigation";
import React, { createContext, useContext, useEffect, useState } from "react";

interface AuthContextType {
  user: any | null;
  loading: boolean;
  orgId?: string;
  accessToken?: string;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEFAULT_ORG_ID = "org_demo";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { getToken, signOut: clerkSignOut } = useClerkAuth();
  const { user: clerkUser, isLoaded } = useUser();
  const [user, setUser] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [orgId, setOrgId] = useState<string | undefined>(DEFAULT_ORG_ID);
  const [accessToken, setAccessToken] = useState<string | undefined>();
  const router = useRouter();
  const pathname = usePathname();

  // Initialize session from Clerk when user loads
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // First, try to load from stored session (for faster initialization)
        const storedSession = getStoredSession();
        if (storedSession) {
          setOrgId(storedSession.orgId);
          setAccessToken(storedSession.accessToken);
          if (storedSession.userId && storedSession.email) {
            setUser({
              id: storedSession.userId,
              email: storedSession.email,
            });
          }
        }

        if (isLoaded) {
          if (clerkUser) {
            // Get Clerk's session token
            const clerkToken = await getToken();

            if (clerkToken) {
              // User is authenticated - exchange Clerk token for backend JWT
              const response = await fetch(
                `${API_BASE_URL}/auth/clerk`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    clerk_token: clerkToken,
                    email: clerkUser.emailAddresses[0]?.emailAddress
                  }),
                }
              );

              if (response.ok) {
                const data = await response.json();
                const resolvedOrgId = data.org_id || DEFAULT_ORG_ID;

                setUser({
                  id: clerkUser.id,
                  email: clerkUser.emailAddresses[0]?.emailAddress,
                  name: `${clerkUser.firstName || ""} ${clerkUser.lastName || ""}`.trim(),
                });
                setOrgId(resolvedOrgId);
                setAccessToken(data.access_token);

                // Save to persistent storage for API calls
                saveSession({
                  accessToken: data.access_token,
                  orgId: resolvedOrgId,
                  userId: clerkUser.id,
                  email: clerkUser.emailAddresses[0]?.emailAddress,
                });
              } else {
                const errorBody = await response.text();
                console.error("Failed to exchange Clerk token:", response.status, response.statusText, errorBody);
                setUser(null);
                setAccessToken(undefined);
              }
            }
          } else {
            // User is not authenticated via Clerk
            // Only clear session if we don't have a stored session
            // (stored session might be valid even if Clerk isn't loaded yet)
            if (!storedSession) {
              clearSession();
              setUser(null);
              setAccessToken(undefined);
              setOrgId(DEFAULT_ORG_ID);
            }
          }
          setLoading(false);
        }
      } catch (error) {
        console.error("Failed to initialize auth:", error);
        clearSession();
        setUser(null);
        setAccessToken(undefined);
        setLoading(false);
      }
    };

    initializeAuth();
  }, [isLoaded, clerkUser, getToken]);

  const signOut = async () => {
    try {
      clearSession();
      setUser(null);
      setAccessToken(undefined);
      setOrgId(DEFAULT_ORG_ID);
      await clerkSignOut({ redirectUrl: "/auth/sign-in" });
    } catch (error) {
      console.error("Sign out failed:", error);
      throw error;
    }
  };

  const refreshSession = async () => {
    try {
      if (clerkUser) {
        const clerkToken = await getToken();
        if (clerkToken) {
          const response = await fetch(
            `${API_BASE_URL}/auth/clerk`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                clerk_token: clerkToken,
                email: clerkUser.emailAddresses[0]?.emailAddress
              }),
            }
          );

          if (response.ok) {
            const data = await response.json();
            const resolvedOrgId = data.org_id || DEFAULT_ORG_ID;

            setAccessToken(data.access_token);
            setOrgId(resolvedOrgId);

            saveSession({
              accessToken: data.access_token,
              orgId: resolvedOrgId,
              userId: clerkUser.id,
              email: clerkUser.emailAddresses[0]?.emailAddress,
            });
          }
        }
      }
    } catch (error) {
      console.error("Session refresh failed:", error);
      throw error;
    }
  };

  const value = {
    user,
    loading,
    orgId,
    accessToken,
    signOut,
    refreshSession,
  };

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
