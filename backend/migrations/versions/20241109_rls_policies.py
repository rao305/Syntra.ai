"""Add Row Level Security policies

Revision ID: 002
Revises: 001
Create Date: 2024-11-09

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS on all tenant-scoped tables
    op.execute("ALTER TABLE orgs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE threads ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_fragments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE provider_keys ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_agent_permissions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_resource_permissions ENABLE ROW LEVEL SECURITY")

    # Create a function to get current org_id from session
    # In production, this would be set by the application via SET LOCAL
    op.execute("""
        CREATE OR REPLACE FUNCTION current_org_id()
        RETURNS TEXT AS $$
        BEGIN
            RETURN current_setting('app.current_org_id', TRUE);
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    # Create a function to get current user_id from session
    op.execute("""
        CREATE OR REPLACE FUNCTION current_user_id()
        RETURNS TEXT AS $$
        BEGIN
            RETURN current_setting('app.current_user_id', TRUE);
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    # RLS Policy for orgs: Users can only see their own org
    op.execute("""
        CREATE POLICY orgs_tenant_isolation ON orgs
        FOR ALL
        USING (id = current_org_id())
    """)

    # RLS Policy for users: Users can only see users in their org
    op.execute("""
        CREATE POLICY users_tenant_isolation ON users
        FOR ALL
        USING (org_id = current_org_id())
    """)

    # RLS Policy for threads: Users can only see threads in their org
    op.execute("""
        CREATE POLICY threads_tenant_isolation ON threads
        FOR ALL
        USING (org_id = current_org_id())
    """)

    # RLS Policy for messages: Via thread's org_id
    op.execute("""
        CREATE POLICY messages_tenant_isolation ON messages
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM threads
                WHERE threads.id = messages.thread_id
                AND threads.org_id = current_org_id()
            )
        )
    """)

    # RLS Policy for memory_fragments: Users can only see fragments in their org
    # Additional policy for private fragments
    op.execute("""
        CREATE POLICY memory_fragments_tenant_isolation ON memory_fragments
        FOR ALL
        USING (org_id = current_org_id())
    """)

    op.execute("""
        CREATE POLICY memory_fragments_private_access ON memory_fragments
        FOR SELECT
        USING (
            org_id = current_org_id()
            AND (
                tier = 'shared'
                OR (tier = 'private' AND user_id = current_user_id())
            )
        )
    """)

    # RLS Policy for audit_logs: Via thread's org_id
    op.execute("""
        CREATE POLICY audit_logs_tenant_isolation ON audit_logs
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM threads
                WHERE threads.id = audit_logs.thread_id
                AND threads.org_id = current_org_id()
            )
        )
    """)

    # RLS Policy for provider_keys: Users can only see their org's keys
    op.execute("""
        CREATE POLICY provider_keys_tenant_isolation ON provider_keys
        FOR ALL
        USING (org_id = current_org_id())
    """)

    # RLS Policy for user_agent_permissions: Via user's org_id
    op.execute("""
        CREATE POLICY user_agent_permissions_tenant_isolation ON user_agent_permissions
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE users.id = user_agent_permissions.user_id
                AND users.org_id = current_org_id()
            )
        )
    """)

    # RLS Policy for agent_resource_permissions: Direct org_id
    op.execute("""
        CREATE POLICY agent_resource_permissions_tenant_isolation ON agent_resource_permissions
        FOR ALL
        USING (org_id = current_org_id())
    """)


def downgrade() -> None:
    # Drop all policies
    op.execute("DROP POLICY IF EXISTS orgs_tenant_isolation ON orgs")
    op.execute("DROP POLICY IF EXISTS users_tenant_isolation ON users")
    op.execute("DROP POLICY IF EXISTS threads_tenant_isolation ON threads")
    op.execute("DROP POLICY IF EXISTS messages_tenant_isolation ON messages")
    op.execute("DROP POLICY IF EXISTS memory_fragments_tenant_isolation ON memory_fragments")
    op.execute("DROP POLICY IF EXISTS memory_fragments_private_access ON memory_fragments")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation ON audit_logs")
    op.execute("DROP POLICY IF EXISTS provider_keys_tenant_isolation ON provider_keys")
    op.execute("DROP POLICY IF EXISTS user_agent_permissions_tenant_isolation ON user_agent_permissions")
    op.execute("DROP POLICY IF EXISTS agent_resource_permissions_tenant_isolation ON agent_resource_permissions")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS current_org_id()")
    op.execute("DROP FUNCTION IF EXISTS current_user_id()")

    # Disable RLS
    op.execute("ALTER TABLE agent_resource_permissions DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_agent_permissions DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE provider_keys DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_fragments DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE messages DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE threads DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE orgs DISABLE ROW LEVEL SECURITY")
