"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  User,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
} from "firebase/auth";
import {
  doc,
  setDoc,
  getDoc,
  serverTimestamp,
  Timestamp,
} from "firebase/firestore";
import { auth, db, googleProvider } from "@/lib/firebase";
import { API_BASE_URL } from "@/lib/api";
import {
  StoredSession,
  clearSession as clearStoredSession,
  getStoredSession,
  saveSession,
} from "@/lib/session";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  orgId?: string;
  accessToken?: string;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<StoredSession | null>(() =>
    typeof window === "undefined" ? null : getStoredSession()
  );

  const syncBackendSession = useCallback(
    async (firebaseUser: User, retryCount = 0) => {
      const maxRetries = 3;
      const retryDelay = 1000; // 1 second

      try {
        const idToken = await firebaseUser.getIdToken(true);

        // Add timeout to fetch request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(new DOMException('Request timeout', 'TimeoutError')), 10000); // 10 second timeout

        try {
          const response = await fetch(`${API_BASE_URL}/auth/firebase`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ id_token: idToken }),
            signal: controller.signal,
          });

          clearTimeout(timeoutId);

          if (!response.ok) {
            const errorBody = await response.text();
            throw new Error(
              `Backend auth failed (${response.status}): ${errorBody}`
            );
          }

          const data = await response.json();
          const newSession: StoredSession = {
            accessToken: data.access_token,
            orgId: data.org_id,
            userId: data.user?.id,
            email: data.user?.email,
          };
          saveSession(newSession);
          setSession(newSession);
        } catch (fetchError) {
          clearTimeout(timeoutId);
          throw fetchError;
        }
      } catch (error: any) {
        console.error("Failed to sync backend session:", error);

        // Retry logic for network errors
        if (retryCount < maxRetries &&
            (error.name === 'AbortError' ||
             error.message === 'Failed to fetch' ||
             error.message.includes('fetch') ||
             error.message.includes('timeout') ||
             error.name === 'TimeoutError')) {
          console.log(`Retrying backend sync (attempt ${retryCount + 1}/${maxRetries})...`);
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          return syncBackendSession(firebaseUser, retryCount + 1);
        }

        throw error;
      }
    },
    []
  );

  const refreshSession = useCallback(async () => {
    if (auth.currentUser) {
      await syncBackendSession(auth.currentUser);
    }
  }, [syncBackendSession]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);

      if (firebaseUser) {
        // Sync backend session first (needed for API calls) - await this
        try {
          await syncBackendSession(firebaseUser);
          // Stop loading after backend session is ready
          setLoading(false);
        } catch (error) {
          console.error("Backend session sync failed - signing out:", error);
          // In production mode, if backend auth fails, sign out completely
          await firebaseSignOut(auth);
          setUser(null);
          clearStoredSession();
          setSession(null);
          setLoading(false);
          throw error; // Re-throw to indicate authentication failure
        }

        // Sync Firestore in the background without blocking
        createOrUpdateUserDoc(firebaseUser).catch((error) => {
          console.warn("Background Firestore sync failed:", error);
        });
      } else {
        clearStoredSession();
        setSession(null);
        setLoading(false);
      }
    });

    return () => unsubscribe();
  }, [syncBackendSession]);

  const createOrUpdateUserDoc = async (firebaseUser: User) => {
    if (!db) {
      console.warn("Firestore not initialized, skipping user document sync");
      return;
    }

    try {
      // Add timeout to prevent hanging on Firestore operations
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error("Firestore operation timeout")), 5000);
      });

      const userRef = doc(db, "users", firebaseUser.uid);

      // Race between timeout and actual operation
      const userSnap = await Promise.race([
        getDoc(userRef),
        timeoutPromise,
      ]) as any;

      const userData = {
        uid: firebaseUser.uid,
        email: firebaseUser.email,
        displayName: firebaseUser.displayName,
        photoURL: firebaseUser.photoURL,
        updatedAt: serverTimestamp(),
      };

      const writePromise = !userSnap.exists()
        ? setDoc(userRef, { ...userData, createdAt: serverTimestamp() })
        : setDoc(userRef, userData, { merge: true });

      // Also timeout the write operation
      await Promise.race([writePromise, timeoutPromise]);
    } catch (error: any) {
      // Gracefully handle Firestore errors - don't block auth
      if (error?.code === "unavailable" || error?.message?.includes("offline")) {
        console.warn("Firestore offline; skipping user document sync");
      } else if (error?.message?.includes("timeout")) {
        console.warn("Firestore operation timed out; database may not be created yet");
      } else {
        console.error("Error creating/updating user document:", error);
      }
    }
  };

  const signInWithGoogle = async () => {
    try {
      setLoading(true);
      await signInWithPopup(auth, googleProvider);
      if (auth.currentUser) {
        try {
          await syncBackendSession(auth.currentUser);
        } catch (error) {
          console.error("Backend sync failed during sign in - signing out:", error);
          // In production mode, if backend auth fails, sign out completely
          await firebaseSignOut(auth);
          setUser(null);
          clearStoredSession();
          setSession(null);
          throw error; // Re-throw to indicate authentication failure
        }
      }
    } catch (error: any) {
      console.error("Error signing in with Google:", error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      await firebaseSignOut(auth);
      setUser(null);
      clearStoredSession();
      setSession(null);
    } catch (error) {
      console.error("Error signing out:", error);
      throw error;
    }
  };

  const value = {
    user,
    loading,
    orgId: session?.orgId,
    accessToken: session?.accessToken,
    signInWithGoogle,
    signOut,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
