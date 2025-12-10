"use client";

import { useAuth } from "@/components/auth/auth-provider";
import { apiFetch } from "@/lib/api";
import { ensureConversationMetadata } from "@/lib/firestore-conversations";
import { useCallback, useEffect, useState } from "react";

export interface Thread {
  id: string;
  title: string | null;
  last_message_preview: string | null;
  last_provider: string | null;
  last_model: string | null;
  created_at: string;
  updated_at: string | null;
  pinned?: boolean;
  archived?: boolean;
}

interface UseThreadsReturn {
  threads: Thread[];
  isLoading: boolean;
  error: Error | null;
  mutate: () => Promise<void>;
  createThread: (params?: {
    title?: string;
    description?: string;
    user_id?: string;
  }) => Promise<{ thread_id: string; created_at: string }>;
  searchThreads: (query: string, archived?: boolean) => Promise<Thread[]>;
  archiveThread: (threadId: string, archived: boolean) => Promise<void>;
  deleteThread: (threadId: string) => Promise<void>;
  deleteAllThreads: () => Promise<void>;
  updateThreadTitle: (threadId: string, title: string) => Promise<void>;
  pinThread: (threadId: string, pinned: boolean) => Promise<void>;
}

const DEFAULT_ORG_ID = "org_demo";

export function useThreads(explicitOrgId?: string): UseThreadsReturn {
  const { orgId: authOrgId, user } = useAuth();
  const orgId = explicitOrgId || authOrgId || DEFAULT_ORG_ID;
  const [threads, setThreads] = useState<Thread[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchThreads = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      // Fetch both active and archived threads so we can toggle between views
      const [activeData, archivedData] = await Promise.all([
        apiFetch<Thread[]>("/threads/?limit=50&archived=false", orgId),
        apiFetch<Thread[]>("/threads/?limit=50&archived=true", orgId)
      ]);

      // Combine both sets
      setThreads([...activeData, ...archivedData]);

      // Removed bulk Firestore sync - it was causing slow page loads
      // Individual threads will sync on-demand when needed
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch threads"));
      console.error("Failed to fetch threads:", err);
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  const createThread = useCallback(
    async (params?: {
      title?: string;
      description?: string;
      user_id?: string;
    }) => {
      const data = await apiFetch<{ thread_id: string; created_at: string }>("/threads/", orgId, {
        method: "POST",
        body: JSON.stringify(params || {}),
      });

      // Try to sync to Firestore asynchronously without blocking
      if (user?.uid && data?.thread_id) {
        // Fire and forget - don't wait for Firestore sync
        ensureConversationMetadata(user.uid, data.thread_id, {
          title: params?.title || "New conversation",
          lastMessagePreview: "",
        }).catch((firestoreError) => {
          console.warn("Failed to sync thread to Firestore:", firestoreError);
        });
      }

      // Don't refresh threads list - it's expensive and unnecessary
      // The sidebar will update via its own subscription or when navigating back

      return data;
    },
    [orgId, user?.uid]
  );

  const searchThreads = useCallback(
    async (query: string, archived?: boolean): Promise<Thread[]> => {
      if (!query.trim()) {
        return [];
      }

      try {
        const params = new URLSearchParams({
          q: query.trim(),
          limit: "50",
        });
        if (archived !== undefined) {
          params.append("archived", archived.toString());
        }

        const response = await apiFetch<Thread[]>(`/threads/search/?${params.toString()}`, orgId);
        return response;
      } catch (err) {
        console.error("Failed to search threads:", err);
        throw err;
      }
    },
    [orgId]
  );

  const archiveThread = useCallback(
    async (threadId: string, archived: boolean): Promise<void> => {
      try {
        await apiFetch(`/threads/${threadId}/archive/?archived=${archived}`, orgId, {
          method: "PATCH",
        });

        // Update local state optimistically
        setThreads((prev) =>
          prev.map((thread) =>
            thread.id === threadId
              ? {
                ...thread,
                archived,
                updated_at: new Date().toISOString(),
              }
              : thread
          )
        );
      } catch (err) {
        console.error("Failed to archive thread:", err);
        throw err;
      }
    },
    [orgId]
  );

  const deleteThread = useCallback(
    async (threadId: string): Promise<void> => {
      try {
        await apiFetch(`/threads/${threadId}/`, orgId, {
          method: "DELETE",
        });

        // Remove from local state
        setThreads((prev) => prev.filter((thread) => thread.id !== threadId));
      } catch (err) {
        console.error("Failed to delete thread:", err);
        throw err;
      }
    },
    [orgId]
  );

  const deleteAllThreads = useCallback(
    async (): Promise<void> => {
      try {
        // Delete all threads by making individual delete requests
        // Note: We could add a bulk delete endpoint on the backend for better performance
        const deletePromises = threads.map((thread) =>
          apiFetch(`/threads/${thread.id}/`, orgId, {
            method: "DELETE",
          })
        );

        await Promise.all(deletePromises);

        // Clear local state
        setThreads([]);
      } catch (err) {
        console.error("Failed to delete all threads:", err);
        throw err;
      }
    },
    [orgId, threads]
  );

  const updateThreadTitle = useCallback(
    async (threadId: string, title: string): Promise<void> => {
      try {
        await apiFetch(`/threads/${threadId}/`, orgId, {
          method: "PATCH",
          body: JSON.stringify({ title }),
        });

        // Update local state
        setThreads((prev) =>
          prev.map((thread) =>
            thread.id === threadId ? { ...thread, title } : thread
          )
        );
      } catch (err) {
        console.error("Failed to update thread title:", err);
        throw err;
      }
    },
    [orgId]
  );

  const pinThread = useCallback(
    async (threadId: string, pinned: boolean): Promise<void> => {
      try {
        await apiFetch(`/threads/${threadId}/settings/`, orgId, {
          method: "PATCH",
          body: JSON.stringify({ pinned }),
        });

        // Update local state
        setThreads((prev) =>
          prev.map((thread) =>
            thread.id === threadId ? { ...thread, pinned } : thread
          )
        );
      } catch (err) {
        console.error("Failed to pin thread:", err);
        throw err;
      }
    },
    [orgId]
  );

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  return {
    threads,
    isLoading,
    error,
    mutate: fetchThreads,
    createThread,
    searchThreads,
    archiveThread,
    deleteThread,
    deleteAllThreads,
    updateThreadTitle,
    pinThread,
  };
}
