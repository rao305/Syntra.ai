-- ============================================================
-- SYNTRA Collaboration Pipeline Verification Queries
-- 
-- Run these against your PostgreSQL database to verify
-- real-world test results.
--
-- Usage: psql -d syntra -f tests/sql/verify_collaborate.sql
-- ============================================================

\echo '═══════════════════════════════════════════════════════════'
\echo '📊 SYNTRA COLLABORATION VERIFICATION QUERIES'
\echo '═══════════════════════════════════════════════════════════'

-- ============================================================
-- 1. Latest Collaborate Message with Full Metadata
-- ============================================================
\echo ''
\echo '🔍 TEST 1: Latest Collaborate Message Metadata'
\echo '─────────────────────────────────────────────'

SELECT 
    id,
    thread_id,
    role,
    created_at,
    provider,
    model,
    LENGTH(content) AS content_length,
    meta->'collaborate'->'mode' AS mode,
    meta->'collaborate'->'run_id' AS run_id,
    meta->'collaborate'->'duration_ms' AS duration_ms,
    meta->'collaborate'->'external_reviews_count' AS external_reviews_count,
    meta->'collaborate'->'truncated' AS truncated
FROM messages 
WHERE role = 'assistant' 
    AND meta->'collaborate' IS NOT NULL
ORDER BY created_at DESC 
LIMIT 5;

-- ============================================================
-- 2. All Stages for Latest Run
-- ============================================================
\echo ''
\echo '🔍 Stage Execution Details (Latest Run)'
\echo '─────────────────────────────────────────────'

SELECT 
    cs.run_id,
    cs.stage_id,
    cs.label,
    cs.provider,
    cs.model,
    cs.status,
    cs.latency_ms,
    cs.started_at,
    cs.finished_at,
    cs.meta->>'error' AS error
FROM collaborate_stages cs
WHERE cs.run_id = (
    SELECT id FROM collaborate_runs 
    ORDER BY created_at DESC 
    LIMIT 1
)
ORDER BY cs.started_at;

-- ============================================================
-- 3. External Reviews for Latest Run
-- ============================================================
\echo ''
\echo '🔍 External Reviews (Latest Run)'
\echo '─────────────────────────────────────────────'

SELECT 
    cr.source AS reviewer,
    cr.provider,
    cr.model,
    cr.latency_ms,
    cr.prompt_tokens,
    cr.completion_tokens,
    LEFT(cr.content, 200) AS content_preview
FROM collaborate_reviews cr
WHERE cr.run_id = (
    SELECT id FROM collaborate_runs 
    ORDER BY created_at DESC 
    LIMIT 1
);

-- ============================================================
-- 4. Collaborate Run Summary
-- ============================================================
\echo ''
\echo '🔍 Collaborate Run Summary (Last 10 Runs)'
\echo '─────────────────────────────────────────────'

SELECT 
    id AS run_id,
    thread_id,
    mode,
    status,
    duration_ms,
    created_at,
    finished_at,
    error_reason
FROM collaborate_runs
ORDER BY created_at DESC
LIMIT 10;

-- ============================================================
-- 5. Incomplete/Failed Runs Check
-- ============================================================
\echo ''
\echo '⚠️  Incomplete or Failed Runs (Last 24 Hours)'
\echo '─────────────────────────────────────────────'

SELECT 
    id AS run_id,
    thread_id,
    status,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at))/60 AS minutes_ago,
    error_reason
FROM collaborate_runs
WHERE status IN ('running', 'error')
    AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- ============================================================
-- 6. Stage Failure Analysis
-- ============================================================
\echo ''
\echo '❌ Stage Failures (Last 24 Hours)'
\echo '─────────────────────────────────────────────'

SELECT 
    cs.stage_id,
    cs.provider,
    cs.model,
    cs.status,
    cs.meta->>'error' AS error,
    cs.started_at
FROM collaborate_stages cs
WHERE cs.status = 'error'
    AND cs.started_at > NOW() - INTERVAL '24 hours'
ORDER BY cs.started_at DESC;

-- ============================================================
-- 7. Provider Performance Statistics
-- ============================================================
\echo ''
\echo '📈 Provider Performance (Last 24 Hours)'
\echo '─────────────────────────────────────────────'

SELECT 
    provider,
    model,
    COUNT(*) AS total_calls,
    AVG(latency_ms)::int AS avg_latency_ms,
    MIN(latency_ms) AS min_latency_ms,
    MAX(latency_ms) AS max_latency_ms,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_count
FROM collaborate_stages
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY provider, model
ORDER BY total_calls DESC;

-- ============================================================
-- 8. External Review Provider Stats
-- ============================================================
\echo ''
\echo '📈 External Review Provider Stats (Last 24 Hours)'
\echo '─────────────────────────────────────────────'

SELECT 
    provider,
    source,
    COUNT(*) AS total_reviews,
    AVG(latency_ms)::int AS avg_latency_ms,
    AVG(LENGTH(content)) AS avg_content_length
FROM collaborate_reviews
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY provider, source
ORDER BY total_reviews DESC;

-- ============================================================
-- 9. Thread Message Verification
-- ============================================================
\echo ''
\echo '🔍 Messages per Thread (Collaborate Threads)'
\echo '─────────────────────────────────────────────'

SELECT 
    t.id AS thread_id,
    t.title,
    COUNT(m.id) AS message_count,
    SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END) AS user_messages,
    SUM(CASE WHEN m.role = 'assistant' THEN 1 ELSE 0 END) AS assistant_messages,
    MAX(m.created_at) AS last_message
FROM threads t
JOIN messages m ON m.thread_id = t.id
WHERE EXISTS (
    SELECT 1 FROM collaborate_runs cr 
    WHERE cr.thread_id = t.id
)
GROUP BY t.id, t.title
ORDER BY MAX(m.created_at) DESC
LIMIT 10;

-- ============================================================
-- 10. Rate Limit Detection (429 Errors)
-- ============================================================
\echo ''
\echo '🚨 Rate Limit Issues (Stages with Rate Limit Errors)'
\echo '─────────────────────────────────────────────'

SELECT 
    stage_id,
    provider,
    model,
    status,
    meta->>'error' AS error,
    started_at
FROM collaborate_stages
WHERE status = 'error'
    AND (
        meta->>'error' LIKE '%429%'
        OR meta->>'error' LIKE '%rate%'
        OR meta->>'error' LIKE '%quota%'
    )
ORDER BY started_at DESC
LIMIT 10;

-- ============================================================
-- 11. Token Usage Summary
-- ============================================================
\echo ''
\echo '💰 Token Usage (Last 24 Hours)'
\echo '─────────────────────────────────────────────'

SELECT 
    provider,
    SUM(prompt_tokens) AS total_prompt_tokens,
    SUM(completion_tokens) AS total_completion_tokens,
    SUM(total_tokens) AS total_tokens,
    COUNT(*) AS api_calls
FROM collaborate_reviews
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY provider
ORDER BY total_tokens DESC;

-- ============================================================
-- 12. Orphaned Runs (No Stages)
-- ============================================================
\echo ''
\echo '⚠️  Orphaned Runs (Runs with No Stages)'
\echo '─────────────────────────────────────────────'

SELECT 
    cr.id,
    cr.thread_id,
    cr.status,
    cr.created_at
FROM collaborate_runs cr
LEFT JOIN collaborate_stages cs ON cs.run_id = cr.id
WHERE cs.id IS NULL
    AND cr.created_at > NOW() - INTERVAL '24 hours'
ORDER BY cr.created_at DESC;

-- ============================================================
-- Summary Statistics
-- ============================================================
\echo ''
\echo '═══════════════════════════════════════════════════════════'
\echo '📊 SUMMARY STATISTICS'
\echo '═══════════════════════════════════════════════════════════'

SELECT 
    (SELECT COUNT(*) FROM collaborate_runs WHERE created_at > NOW() - INTERVAL '24 hours') AS runs_24h,
    (SELECT COUNT(*) FROM collaborate_runs WHERE status = 'success' AND created_at > NOW() - INTERVAL '24 hours') AS successful_24h,
    (SELECT COUNT(*) FROM collaborate_runs WHERE status = 'error' AND created_at > NOW() - INTERVAL '24 hours') AS failed_24h,
    (SELECT COUNT(*) FROM collaborate_runs WHERE status = 'running' AND created_at > NOW() - INTERVAL '24 hours') AS incomplete_24h,
    (SELECT AVG(duration_ms)::int FROM collaborate_runs WHERE status = 'success' AND created_at > NOW() - INTERVAL '24 hours') AS avg_duration_ms,
    (SELECT COUNT(DISTINCT provider) FROM collaborate_reviews WHERE created_at > NOW() - INTERVAL '24 hours') AS active_reviewers;

\echo ''
\echo '✅ Verification complete'
\echo ''








