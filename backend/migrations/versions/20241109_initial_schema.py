"""Initial schema with RLS policies

Revision ID: 001
Revises:
Create Date: 2024-11-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'member', 'viewer')")
    op.execute("CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system')")
    op.execute("CREATE TYPE memory_tier AS ENUM ('private', 'shared')")
    op.execute("CREATE TYPE provider_type AS ENUM ('perplexity', 'openai', 'gemini', 'openrouter')")

    # Create orgs table
    op.create_table(
        'orgs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),
        sa.Column('subscription_status', sa.String(), nullable=True),
        sa.Column('seats_licensed', sa.Integer(), default=0),
        sa.Column('seats_used', sa.Integer(), default=0),
        sa.Column('requests_per_day', sa.Integer(), nullable=True),
        sa.Column('tokens_per_day', sa.Integer(), nullable=True),
        sa.Column('sso_enabled', sa.Boolean(), default=False),
        sa.Column('saml_metadata_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('stripe_customer_id'),
        sa.UniqueConstraint('stripe_subscription_id')
    )
    op.create_index('ix_orgs_slug', 'orgs', ['slug'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'member', 'viewer', name='user_role'), nullable=False),
        sa.Column('email_verified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_org_id', 'users', ['org_id'])

    # Create threads table
    op.create_table(
        'threads',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('creator_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('last_provider', sa.String(), nullable=True),
        sa.Column('last_model', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_threads_org_id', 'threads', ['org_id'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('role', postgresql.ENUM('user', 'assistant', 'system', name='message_role'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('provider_message_id', sa.String(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('citations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_messages_thread_id', 'messages', ['thread_id'])

    # Create memory_fragments table
    op.create_table(
        'memory_fragments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('tier', postgresql.ENUM('private', 'shared', name='memory_tier'), nullable=False),
        sa.Column('vector_id', sa.String(), nullable=True),
        sa.Column('provenance', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_memory_fragments_org_id', 'memory_fragments', ['org_id'])
    op.create_index('ix_memory_fragments_tier', 'memory_fragments', ['tier'])
    op.create_index('ix_memory_fragments_vector_id', 'memory_fragments', ['vector_id'])
    op.create_index('ix_memory_fragments_content_hash', 'memory_fragments', ['content_hash'])
    op.create_index('ix_memory_org_tier', 'memory_fragments', ['org_id', 'tier'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('message_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('fragments_included', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('fragments_excluded', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('package_hash', sa.String(), nullable=False),
        sa.Column('response_hash', sa.String(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_audit_logs_thread_id', 'audit_logs', ['thread_id'])

    # Create provider_keys table
    op.create_table(
        'provider_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('provider', postgresql.ENUM('perplexity', 'openai', 'gemini', 'openrouter', name='provider_type'), nullable=False),
        sa.Column('encrypted_key', sa.LargeBinary(), nullable=False),
        sa.Column('key_name', sa.String(), nullable=True),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.String(), default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_provider_keys_org_id', 'provider_keys', ['org_id'])
    op.create_index('ix_provider_keys_org_provider', 'provider_keys', ['org_id', 'provider'])

    # Create user_agent_permissions table
    op.create_table(
        'user_agent_permissions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('agent_key', sa.String(), nullable=False),
        sa.Column('can_invoke', sa.Boolean(), default=True, nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_user_agent_permissions_user_id', 'user_agent_permissions', ['user_id'])
    op.create_index('ix_user_agent_permissions_agent_key', 'user_agent_permissions', ['agent_key'])
    op.create_index('ix_user_agent_perm', 'user_agent_permissions', ['user_id', 'agent_key'])

    # Create agent_resource_permissions table
    op.create_table(
        'agent_resource_permissions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('agent_key', sa.String(), nullable=False),
        sa.Column('resource_key', sa.String(), nullable=False),
        sa.Column('can_access', sa.Boolean(), default=True, nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_agent_resource_permissions_org_id', 'agent_resource_permissions', ['org_id'])
    op.create_index('ix_agent_resource_permissions_agent_key', 'agent_resource_permissions', ['agent_key'])
    op.create_index('ix_agent_resource_permissions_resource_key', 'agent_resource_permissions', ['resource_key'])
    op.create_index('ix_agent_resource_perm', 'agent_resource_permissions', ['agent_key', 'resource_key'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('agent_resource_permissions')
    op.drop_table('user_agent_permissions')
    op.drop_table('provider_keys')
    op.drop_table('audit_logs')
    op.drop_table('memory_fragments')
    op.drop_table('messages')
    op.drop_table('threads')
    op.drop_table('users')
    op.drop_table('orgs')

    # Drop ENUM types
    op.execute("DROP TYPE provider_type")
    op.execute("DROP TYPE memory_tier")
    op.execute("DROP TYPE message_role")
    op.execute("DROP TYPE user_role")
