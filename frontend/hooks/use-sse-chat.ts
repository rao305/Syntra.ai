import { getStoredSession } from '@/lib/session';
import { useCallback, useRef, useState } from 'react';

export type StreamState = {
  loading: boolean;
  cancelled: boolean;
  cache_hit: boolean;
  content: string;
  ttft_ms?: number;
  error?: string;
  media?: Array<{
    type: 'image' | 'graph';
    url: string;
    alt?: string;
    mime_type?: string;
  }>;
};

export function useSSEChat() {
  const [state, setState] = useState<StreamState>({
    loading: false,
    cancelled: false,
    cache_hit: false,
    content: ''
  });
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (payload: any) => {
    // Reset state immediately to make the Stop button feel snappy
    setState({ loading: true, cancelled: false, cache_hit: false, content: '' });

    const controller = new AbortController();
    abortRef.current = controller;

    const startedAt = performance.now();
    let sawFirstDelta = false;

    try {
      const session = getStoredSession();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      };
      if (session?.orgId) {
        headers['x-org-id'] = session.orgId;
      }
      if (session?.accessToken) {
        headers['Authorization'] = `Bearer ${session.accessToken}`;
      }

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      for (; ;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        let eom = buf.indexOf('\n\n');
        while (eom !== -1) {
          const raw = buf.slice(0, eom);
          buf = buf.slice(eom + 2);
          eom = buf.indexOf('\n\n');

          // Parse one SSE event
          // Support lines like: "event:meta" and "data:{...}" or "data: token"
          let eventType = 'message';
          let dataLine = '';
          for (const line of raw.split('\n')) {
            if (line.startsWith('event:')) eventType = line.slice(6).trim();
            if (line.startsWith('data:')) dataLine += line.slice(5).trim();
          }

          if (!dataLine) continue;

          if (eventType === 'meta') {
            try {
              const meta = JSON.parse(dataLine);
              if (typeof meta.cache_hit === 'boolean') {
                setState(s => ({ ...s, cache_hit: meta.cache_hit }));
              }
            } catch { }
            continue;
          }

          // Handle media events (images/graphs)
          if (eventType === 'media') {
            try {
              const mediaData = JSON.parse(dataLine);
              setState(s => ({
                ...s,
                media: [...(s.media || []), {
                  type: mediaData.type === 'graph' ? 'graph' : 'image',
                  url: mediaData.url,
                  alt: mediaData.alt,
                  mime_type: mediaData.mime_type
                }]
              }));
            } catch { }
            continue;
          }

          // Normal token delta
          if (!sawFirstDelta) {
            sawFirstDelta = true;
            const ttft = performance.now() - startedAt;
            setState(s => ({ ...s, ttft_ms: Math.round(ttft) }));
          }
          setState(s => ({ ...s, content: s.content + dataLine }));
        }
      }

      setState(s => ({ ...s, loading: false }));
    } catch (err: any) {
      if (controller.signal.aborted) {
        setState(s => ({ ...s, loading: false, cancelled: true }));
      } else {
        setState(s => ({ ...s, loading: false, error: String(err?.message || err) }));
      }
    }
  }, []);

  const cancel = useCallback(() => {
    // Immediate UX feedback; abort in-flight network
    setState(s => ({ ...s, cancelled: true, loading: false }));
    abortRef.current?.abort();
  }, []);

  return { state, start, cancel } as const;
}
