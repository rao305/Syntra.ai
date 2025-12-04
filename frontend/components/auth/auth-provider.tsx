"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { auth } from "@/lib/firebase";
import {
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  User as FirebaseUser,
} from "firebase/auth";
import { useRouter } from "next/navigation";

interface AuthContextType {
  user: any | null;
  loading: boolean;
  orgId?: string;
  accessToken?: string;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [orgId, setOrgId] = useState<string | undefined>();
  const [accessToken, setAccessToken] = useState<string | undefined>();
  const router = useRouter();

  // Listen for Firebase auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          // Get ID token from Firebase
          const idToken = await firebaseUser.getIdToken();

          // Exchange Firebase token for our backend JWT
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/firebase`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id_token: idToken }),
            }
          );

          if (!response.ok) {
            throw new Error(`Auth failed: ${response.statusText}`);
          }

          const data = await response.json();
          setUser(data.user);
          setOrgId(data.org_id);
          setAccessToken(data.access_token);

          // Store token in session storage (will be cleared on tab close)
          sessionStorage.setItem("access_token", data.access_token);
          sessionStorage.setItem("org_id", data.org_id);
        } catch (error) {
          console.error("Failed to exchange Firebase token:", error);
          setUser(null);
          setAccessToken(undefined);
        }
      } else {
        setUser(null);
        setOrgId(undefined);
        setAccessToken(undefined);
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("org_id");
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const signInWithGoogle = async () => {
    try {
      setLoading(true);
      const provider = new GoogleAuthProvider();
      // Request email scope
      provider.addScopes(["email", "profile"]);
      const result = await signInWithPopup(auth, provider);

      // Get ID token
      const idToken = await result.user.getIdToken();

      // Exchange for backend JWT
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/firebase`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id_token: idToken }),
        }
      );

      if (!response.ok) {
        throw new Error(`Auth exchange failed: ${response.statusText}`);
      }

      const data = await response.json();
      setUser(data.user);
      setOrgId(data.org_id);
      setAccessToken(data.access_token);

      // Store tokens
      sessionStorage.setItem("access_token", data.access_token);
      sessionStorage.setItem("org_id", data.org_id);

      // Redirect to conversations
      router.push("/conversations");
    } catch (error) {
      console.error("Google sign-in failed:", error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      await firebaseSignOut(auth);
      setUser(null);
      setAccessToken(undefined);
      setOrgId(undefined);
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("org_id");
      router.push("/auth/sign-in");
    } catch (error) {
      console.error("Sign out failed:", error);
      throw error;
    }
  };

  const refreshSession = async () => {
    try {
      const firebaseUser = auth.currentUser;
      if (firebaseUser) {
        const idToken = await firebaseUser.getIdToken(true); // Force refresh
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/firebase`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_token: idToken }),
          }
        );

        if (!response.ok) {
          throw new Error("Token refresh failed");
        }

        const data = await response.json();
        setAccessToken(data.access_token);
        sessionStorage.setItem("access_token", data.access_token);
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
    signInWithGoogle,
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
