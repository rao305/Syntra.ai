/**
 * Memory Debug API Route
 * 
 * DEV / ADMIN TOOL - Read-only memory inspection
 * 
 * This endpoint allows admins to inspect what has been stored in Supermemory
 * for debugging and monitoring purposes.
 * 
 * Endpoint: GET /api/memory-debug
 * Query params:
 *   - userId?: string
 *   - sessionId?: string
 *   - query?: string (search term)
 */

import { NextRequest, NextResponse } from 'next/server';

const SUPERMEMORY_API_KEY = process.env.SUPERMEMORY_API_KEY;

interface MemoryDebugResponse {
  userId?: string;
  sessionId?: string;
  query?: string;
  memories: Array<{
    id: string;
    text: string;
    createdAt?: string;
    metadata?: Record<string, any>;
  }>;
  error?: string;
}

export async function GET(request: NextRequest) {
  // Check if Supermemory is configured
  if (!SUPERMEMORY_API_KEY) {
    return NextResponse.json(
      {
        userId: undefined,
        sessionId: undefined,
        query: undefined,
        memories: [],
        error: 'Supermemory is not configured. SUPERMEMORY_API_KEY is not set.',
      } as MemoryDebugResponse,
      { status: 503 }
    );
  }

  try {
    const searchParams = request.nextUrl.searchParams;
    const userId = searchParams.get('userId') || undefined;
    const sessionId = searchParams.get('sessionId') || undefined;
    const query = searchParams.get('query') || undefined;

    // Build search query
    // If no query provided, we'll search for all memories for the user/session
    const searchQuery = query || (userId ? `userId:${userId}` : '') || (sessionId ? `sessionId:${sessionId}` : '') || '';

    // Call Supermemory API directly
    // Note: This uses the Supermemory REST API
    // The @supermemory/tools package wraps this, but for direct access we use the API
    const supermemoryApiUrl = 'https://api.supermemory.ai/v1/memories/search';
    
    const response = await fetch(supermemoryApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPERMEMORY_API_KEY}`,
      },
      body: JSON.stringify({
        query: searchQuery,
        userId: userId,
        sessionId: sessionId,
        limit: 50, // Limit results
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        {
          userId,
          sessionId,
          query: searchQuery,
          memories: [],
          error: `Supermemory API error: ${response.status} ${errorText}`,
        } as MemoryDebugResponse,
        { status: response.status }
      );
    }

    const data = await response.json();

    // Transform Supermemory response to our format
    const memories = (data.memories || []).map((mem: any) => ({
      id: mem.id || mem.memory_id || 'unknown',
      text: mem.text || mem.content || '',
      createdAt: mem.created_at || mem.createdAt || undefined,
      metadata: {
        userId: mem.user_id || mem.userId,
        sessionId: mem.session_id || mem.sessionId,
        ...mem.metadata,
      },
    }));

    return NextResponse.json({
      userId,
      sessionId,
      query: searchQuery,
      memories,
    } as MemoryDebugResponse);

  } catch (error) {
    console.error('Memory debug API error:', error);
    return NextResponse.json(
      {
        userId: undefined,
        sessionId: undefined,
        query: undefined,
        memories: [],
        error: `Internal error: ${error instanceof Error ? error.message : String(error)}`,
      } as MemoryDebugResponse,
      { status: 500 }
    );
  }
}








