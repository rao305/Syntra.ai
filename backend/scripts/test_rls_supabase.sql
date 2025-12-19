-- Comprehensive RLS Testing Script for Supabase
-- Run this in Supabase SQL Editor to validate RLS policies are working correctly

-- ============================================================================
-- SETUP: Create test data in two different organizations
-- ============================================================================

-- Insert test organizations
INSERT INTO orgs (id, name, created_at, updated_at)
VALUES
  ('org_test_a', 'Test Organization A', now(), now()),
  ('org_test_b', 'Test Organization B', now(), now())
ON CONFLICT (id) DO NOTHING;

-- Insert test users
INSERT INTO users (id, org_id, email, full_name, role, created_at, updated_at)
VALUES
  ('user_test_a', 'org_test_a', 'user_a@test.com', 'User A', 'member', now(), now()),
  ('user_test_b', 'org_test_b', 'user_b@test.com', 'User B', 'member', now(), now())
ON CONFLICT (id) DO NOTHING;

-- Insert test threads
INSERT INTO threads (id, org_id, created_by, title, created_at, updated_at)
VALUES
  ('thread_a', 'org_test_a', 'user_test_a', 'Thread in Org A', now(), now()),
  ('thread_b', 'org_test_b', 'user_test_b', 'Thread in Org B', now(), now())
ON CONFLICT (id) DO NOTHING;

-- Insert test messages
INSERT INTO messages (id, thread_id, role, content, created_at, updated_at)
VALUES
  ('msg_a', 'thread_a', 'user', 'Message in Thread A', now(), now()),
  ('msg_b', 'thread_b', 'user', 'Message in Thread B', now(), now())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- TEST 1: Test RLS Function for current_org_id
-- ============================================================================
-- Set context for org_test_a
SET app.current_org_id = 'org_test_a';
SET app.current_user_id = 'user_test_a';

SELECT 'TEST 1: RLS Context Set' as test_name;
SELECT current_setting('app.current_org_id', true) as context_org_id;
SELECT current_setting('app.current_user_id', true) as context_user_id;

-- ============================================================================
-- TEST 2: Verify RLS Isolation - Should ONLY see org_test_a data
-- ============================================================================
SELECT 'TEST 2: ORG Isolation - Querying orgs (should see only org_test_a)' as test_name;
SELECT id, name FROM orgs ORDER BY id;

SELECT 'TEST 2: USER Isolation - Querying users (should see only org_test_a users)' as test_name;
SELECT id, org_id, email FROM users ORDER BY id;

SELECT 'TEST 2: THREAD Isolation - Querying threads (should see only org_test_a threads)' as test_name;
SELECT id, org_id, title FROM threads ORDER BY id;

SELECT 'TEST 2: MESSAGE Isolation - Querying messages via thread (should see only thread_a messages)' as test_name;
SELECT m.id, m.thread_id, m.content FROM messages m WHERE m.thread_id = 'thread_a';

-- ============================================================================
-- TEST 3: Verify Cross-Org Access is BLOCKED
-- ============================================================================
SELECT 'TEST 3: Cross-Org Access Attempt - Trying to query org_test_b thread' as test_name;
SELECT id, org_id, title FROM threads WHERE id = 'thread_b';
-- ^^ Should return 0 rows (RLS blocked it)

-- ============================================================================
-- TEST 4: Switch Context to org_test_b
-- ============================================================================
RESET app.current_org_id;
RESET app.current_user_id;
SET app.current_org_id = 'org_test_b';
SET app.current_user_id = 'user_test_b';

SELECT 'TEST 4: Context Switched to org_test_b' as test_name;
SELECT current_setting('app.current_org_id', true) as context_org_id;

-- ============================================================================
-- TEST 5: Verify Org B Can ONLY See Org B Data
-- ============================================================================
SELECT 'TEST 5: ORG Isolation (org_test_b) - Querying orgs (should see only org_test_b)' as test_name;
SELECT id, name FROM orgs ORDER BY id;

SELECT 'TEST 5: THREAD Isolation (org_test_b) - Querying threads (should see only thread_b)' as test_name;
SELECT id, org_id, title FROM threads ORDER BY id;

-- ============================================================================
-- TEST 6: Verify Org B Cannot Access Org A Data
-- ============================================================================
SELECT 'TEST 6: Cross-Org Block - Trying to query org_test_a thread (should return 0 rows)' as test_name;
SELECT id, org_id, title FROM threads WHERE id = 'thread_a';
-- ^^ Should return 0 rows (RLS blocked it)

-- ============================================================================
-- TEST 7: Test Memory Fragment RLS (if memory_fragments exists)
-- ============================================================================
RESET app.current_org_id;
RESET app.current_user_id;
SET app.current_org_id = 'org_test_a';
SET app.current_user_id = 'user_test_a';

-- Insert test memory fragment for org_test_a
INSERT INTO memory_fragments (
  id, org_id, user_id, text, tier, content_hash, provenance, created_at, updated_at
)
VALUES (
  'mem_a', 'org_test_a', 'user_test_a', 'Test memory for Org A', 'private',
  'hash_a', '{"provider":"openai","model":"gpt-4"}', now(), now()
)
ON CONFLICT (id) DO NOTHING;

-- Insert test memory fragment for org_test_b
INSERT INTO memory_fragments (
  id, org_id, user_id, text, tier, content_hash, provenance, created_at, updated_at
)
VALUES (
  'mem_b', 'org_test_b', 'user_test_b', 'Test memory for Org B', 'private',
  'hash_b', '{"provider":"openai","model":"gpt-4"}', now(), now()
)
ON CONFLICT (id) DO NOTHING;

SELECT 'TEST 7: MEMORY Isolation (org_test_a) - Should see only mem_a' as test_name;
SELECT id, org_id, tier FROM memory_fragments ORDER BY id;

-- Switch to org_test_b
RESET app.current_org_id;
RESET app.current_user_id;
SET app.current_org_id = 'org_test_b';
SET app.current_user_id = 'user_test_b';

SELECT 'TEST 7: MEMORY Isolation (org_test_b) - Should see only mem_b' as test_name;
SELECT id, org_id, tier FROM memory_fragments ORDER BY id;

-- ============================================================================
-- TEST 8: Verify Audit Log RLS
-- ============================================================================
RESET app.current_org_id;
RESET app.current_user_id;
SET app.current_org_id = 'org_test_a';
SET app.current_user_id = 'user_test_a';

INSERT INTO audit_logs (id, org_id, action, resource_type, created_at)
VALUES ('audit_a', 'org_test_a', 'CREATE', 'thread', now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO audit_logs (id, org_id, action, resource_type, created_at)
VALUES ('audit_b', 'org_test_b', 'CREATE', 'thread', now())
ON CONFLICT (id) DO NOTHING;

SELECT 'TEST 8: AUDIT LOG Isolation (org_test_a) - Should see only audit_a' as test_name;
SELECT id, org_id, action FROM audit_logs ORDER BY id;

RESET app.current_org_id;
RESET app.current_user_id;
SET app.current_org_id = 'org_test_b';
SET app.current_user_id = 'user_test_b';

SELECT 'TEST 8: AUDIT LOG Isolation (org_test_b) - Should see only audit_b' as test_name;
SELECT id, org_id, action FROM audit_logs ORDER BY id;

-- ============================================================================
-- CLEANUP: Reset context
-- ============================================================================
RESET app.current_org_id;
RESET app.current_user_id;

SELECT 'All tests completed. Review results above for RLS effectiveness.' as summary;

-- ============================================================================
-- EXPECTED RESULTS:
-- ============================================================================
-- TEST 1: Should show context values set correctly
-- TEST 2: When context is org_test_a, should see ONLY org_test_a data
-- TEST 3: Should return 0 rows (RLS blocks cross-org access)
-- TEST 4: Context successfully switched to org_test_b
-- TEST 5: When context is org_test_b, should see ONLY org_test_b data
-- TEST 6: Should return 0 rows (RLS blocks Org B from accessing Org A data)
-- TEST 7: Memory fragments show org isolation working
-- TEST 8: Audit logs show org isolation working
--
-- IF ALL TESTS PASS: RLS is working correctly! ✅
-- IF ANY TEST FAILS: RLS policies need to be reviewed ❌
