/**
 * API Keys Settings Page
 * Allows users to manage their AI provider API keys
 */

'use client';

import { useState, useEffect } from 'react';
import { Plus, Eye, EyeOff, Trash2, Check, X, ExternalLink, RefreshCw } from 'lucide-react';

interface Provider {
  id: string;
  name: string;
  description: string;
  signup_url: string;
  docs_url: string;
}

interface APIKey {
  id: string;
  provider: string;
  key_name: string | null;
  is_active: boolean;
  validation_status: string;
  last_validated_at: string | null;
  total_requests: number;
  total_tokens_used: number;
  last_used_at: string | null;
  created_at: string;
}

export default function APIKeysPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchProviders();
    fetchAPIKeys();
  }, []);

  const fetchProviders = async () => {
    try {
      const res = await fetch('/api/api-keys/providers');
      const data = await res.json();
      setProviders(data.providers);
    } catch (error) {
      console.error('Failed to fetch providers:', error);
    }
  };

  const fetchAPIKeys = async () => {
    try {
      const res = await fetch('/api/api-keys/');
      const data = await res.json();
      setApiKeys(data);
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">API Keys</h1>
          <p className="text-gray-400 mt-2">
            Manage your AI provider API keys. Syntra uses your keys to access AI models.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition"
        >
          <Plus className="w-4 h-4" />
          Add API Key
        </button>
      </div>

      {/* No Keys State */}
      {apiKeys.length === 0 && (
        <div className="text-center py-16 bg-gray-800/50 rounded-xl border border-gray-700">
          <div className="text-6xl mb-4">🔑</div>
          <h2 className="text-xl font-semibold text-white mb-2">No API Keys Yet</h2>
          <p className="text-gray-400 mb-6 max-w-md mx-auto">
            Add your AI provider API keys to start using Syntra. Your keys are encrypted and never shared.
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition"
          >
            Add Your First API Key
          </button>
        </div>
      )}

      {/* API Keys List */}
      {apiKeys.length > 0 && (
        <div className="space-y-4">
          {apiKeys.map((key) => (
            <APIKeyCard
              key={key.id}
              apiKey={key}
              providers={providers}
              onDelete={() => fetchAPIKeys()}
              onValidate={() => fetchAPIKeys()}
            />
          ))}
        </div>
      )}

      {/* Add API Key Modal */}
      {showAddModal && (
        <AddAPIKeyModal
          providers={providers}
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            fetchAPIKeys();
          }}
        />
      )}

      {/* Information Section */}
      <div className="mt-12 p-6 bg-blue-500/10 border border-blue-500/30 rounded-xl">
        <h3 className="text-lg font-semibold text-blue-400 mb-3">
          How It Works
        </h3>
        <ul className="space-y-2 text-gray-300 text-sm">
          <li className="flex items-start gap-2">
            <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
            <span>You provide API keys from AI providers (OpenAI, Gemini, etc.)</span>
          </li>
          <li className="flex items-start gap-2">
            <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
            <span>Syntra securely encrypts and stores your keys</span>
          </li>
          <li className="flex items-start gap-2">
            <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
            <span>Our intelligent router selects the best model for each task</span>
          </li>
          <li className="flex items-start gap-2">
            <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
            <span>You pay providers directly based on usage - no markup!</span>
          </li>
          <li className="flex items-start gap-2">
            <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
            <span>Syntra subscription covers routing, collaboration, and premium features</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

// API Key Card Component
function APIKeyCard({ apiKey, providers, onDelete, onValidate }: any) {
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [validating, setValidating] = useState(false);

  const provider = providers.find((p: Provider) => p.id === apiKey.provider);

  const handleValidate = async () => {
    setValidating(true);
    try {
      await fetch(`/api/api-keys/${apiKey.id}/validate`, { method: 'POST' });
      onValidate();
    } catch (error) {
      console.error('Validation failed:', error);
    } finally {
      setValidating(false);
    }
  };

  const handleDelete = async () => {
    try {
      await fetch(`/api/api-keys/${apiKey.id}`, { method: 'DELETE' });
      onDelete();
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  return (
    <div className="p-6 bg-gray-800/50 rounded-xl border border-gray-700">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-lg font-semibold text-white">
              {provider?.name || apiKey.provider}
            </h3>

            {/* Status Badge */}
            {apiKey.validation_status === 'valid' && (
              <span className="flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
                <Check className="w-3 h-3" />
                Valid
              </span>
            )}
            {apiKey.validation_status === 'invalid' && (
              <span className="flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">
                <X className="w-3 h-3" />
                Invalid
              </span>
            )}
            {apiKey.validation_status === 'pending' && (
              <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded-full">
                Pending
              </span>
            )}
          </div>

          <p className="text-sm text-gray-400 mb-4">{apiKey.key_name || `${provider?.name} Key`}</p>

          {/* Usage Stats */}
          <div className="flex gap-6 text-sm">
            <div>
              <span className="text-gray-500">Requests:</span>
              <span className="ml-2 text-white font-medium">
                {apiKey.total_requests.toLocaleString()}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Tokens:</span>
              <span className="ml-2 text-white font-medium">
                {apiKey.total_tokens_used.toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={handleValidate}
            disabled={validating}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition"
            title="Validate API key"
          >
            {validating ? <RefreshCw className="w-4 h-4 animate-spin" /> : '🔄'}
          </button>
          <button
            onClick={() => setShowConfirmDelete(true)}
            className="p-2 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded-lg transition"
            title="Delete API key"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Delete Confirmation */}
      {showConfirmDelete && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-sm text-red-400 mb-3">
            Are you sure you want to delete this API key? This action cannot be undone.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleDelete}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg transition"
            >
              Yes, Delete
            </button>
            <button
              onClick={() => setShowConfirmDelete(false)}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Add API Key Modal Component
function AddAPIKeyModal({ providers, onClose, onSuccess }: any) {
  const [selectedProvider, setSelectedProvider] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [keyName, setKeyName] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const provider = providers.find((p: Provider) => p.id === selectedProvider);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/api-keys/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: selectedProvider,
          api_key: apiKey,
          key_name: keyName || `${provider?.name} Key`,
          validate: true
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to add API key');
      }

      onSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-2xl max-w-2xl w-full p-6 border border-gray-700">
        <h2 className="text-2xl font-bold text-white mb-4">Add API Key</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Provider
            </label>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              required
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
            >
              <option value="">Select a provider...</option>
              {providers.map((p: Provider) => (
                <option key={p.id} value={p.id}>
                  {p.name} - {p.description}
                </option>
              ))}
            </select>
          </div>

          {/* Provider Info */}
          {provider && (
            <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <p className="text-sm text-gray-300 mb-2">
                Don't have an API key yet?
              </p>
              <div className="flex gap-3">
                <a
                  href={provider.signup_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300"
                >
                  Get API Key
                  <ExternalLink className="w-3 h-3" />
                </a>
                <a
                  href={provider.docs_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300"
                >
                  Documentation
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          )}

          {/* API Key Input */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              API Key
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
                placeholder="sk-..."
                className="w-full px-4 py-2 pr-12 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Key Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Key Name (Optional)
            </label>
            <input
              type="text"
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              placeholder="Personal Key, Work Key, etc."
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 justify-end pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !selectedProvider || !apiKey}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition"
            >
              {loading ? 'Adding...' : 'Add API Key'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


