-- Migration: Add user_api_keys table and api_key_audit_log table

-- Create user_api_keys table
CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,

    -- Encrypted API key
    encrypted_key TEXT NOT NULL,
    encryption_salt TEXT NOT NULL,

    -- Key metadata
    key_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    last_validated_at TIMESTAMP WITH TIME ZONE,
    validation_status VARCHAR(20) DEFAULT 'pending',

    -- Usage tracking
    total_requests INTEGER DEFAULT 0,
    total_tokens_used BIGINT DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(user_id, provider, key_name),
    CHECK (provider IN ('openai', 'gemini', 'anthropic', 'perplexity', 'kimi'))
);

-- Create indexes for user_api_keys
CREATE INDEX idx_user_api_keys_user_id ON user_api_keys(user_id);
CREATE INDEX idx_user_api_keys_provider ON user_api_keys(provider);
CREATE INDEX idx_user_api_keys_active ON user_api_keys(user_id, is_active);

-- Create api_key_audit_log table
CREATE TABLE api_key_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_api_key_id UUID NOT NULL REFERENCES user_api_keys(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),

    action VARCHAR(50) NOT NULL,  -- 'created', 'validated', 'used', 'updated', 'deleted'
    ip_address INET,
    user_agent TEXT,

    -- Additional metadata
    metadata JSON DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for api_key_audit_log
CREATE INDEX idx_api_key_audit_user ON api_key_audit_log(user_id, created_at DESC);
CREATE INDEX idx_api_key_audit_key ON api_key_audit_log(user_api_key_id, created_at DESC);

-- Create updated_at trigger for user_api_keys
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_api_keys_updated_at
    BEFORE UPDATE ON user_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


