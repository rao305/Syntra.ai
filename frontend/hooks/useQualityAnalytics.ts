"use client";

import { useState, useEffect } from "react";
import type { QualityAnalyticsData } from "@/components/collaborate/QualityAnalyticsDashboard";

interface UseQualityAnalyticsOptions {
  threadId?: string;
  orgId?: string;
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseQualityAnalyticsResult {
  data: QualityAnalyticsData[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useQualityAnalytics(
  options: UseQualityAnalyticsOptions = {}
): UseQualityAnalyticsResult {
  const {
    threadId,
    orgId,
    limit = 100,
    autoRefresh = false,
    refreshInterval = 30000,
  } = options;

  const [data, setData] = useState<QualityAnalyticsData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = new URLSearchParams();
      if (threadId) params.append("thread_id", threadId);
      if (orgId) params.append("org_id", orgId);
      params.append("limit", limit.toString());

      const response = await fetch(
        `/api/analytics/quality?${params.toString()}`,
        {
          headers: {
            "Content-Type": "application/json",
            ...(orgId && { "x-org-id": orgId }),
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch quality analytics: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result.data || []);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
      console.error("Error fetching quality analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [threadId, orgId, limit]);

  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}

export default useQualityAnalytics;
