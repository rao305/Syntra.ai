"use client";

import React, { createContext, useContext, useState } from "react";

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
  const [loading, setLoading] = useState(false);
  const [orgId, setOrgId] = useState<string | undefined>("org_demo");
  const [accessToken, setAccessToken] = useState<string | undefined>();

  const signInWithGoogle = async () => {
    console.log("Google sign-in not configured - Firebase disabled");
  };

  const signOut = async () => {
    setUser(null);
    setAccessToken(undefined);
  };

  const refreshSession = async () => {
    console.log("Session refresh not configured - Firebase disabled");
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
