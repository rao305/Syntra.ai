/**
 * Cost monitoring dashboard component.
 */

import React, { useState, useEffect } from 'react';

interface CostSummary {
  total_cost: number;
  total_requests: number;
  avg_cost_per_request: number;
  estimated_savings_from_routing: number;
  cost_by_model: Record<string, number>;
  tokens_by_model: Record<string, number>;
  period_start: string;
  period_end: string;
}

interface BudgetStatus {
  daily: {
    spent: number;
    budget: number | null;
    remaining: number | null;
    percentage: number | null;
  };
  monthly: {
    spent: number;
    budget: number | null;
    remaining: number | null;
    percentage: number | null;
  };
}

export const CostDashboard: React.FC = () => {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [budgetStatus, setBudgetStatus] = useState<BudgetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCostData();
    const interval = setInterval(fetchCostData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchCostData = async () => {
    try {
      setError(null);

      // Fetch cost summary
      const summaryResponse = await fetch('/api/router/costs/summary');
      if (!summaryResponse.ok) throw new Error('Failed to fetch cost summary');
      const summaryData = await summaryResponse.json();
      setSummary(summaryData);

      // Fetch budget status
      const budgetResponse = await fetch('/api/router/costs/budget/status');
      if (!budgetResponse.ok) throw new Error('Failed to fetch budget status');
      const budgetData = await budgetResponse.json();
      setBudgetStatus(budgetData);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch cost data');
      console.error('Cost dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-4 animate-pulse">
        <div className="h-32 bg-gray-800 rounded-lg mb-4"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-800 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <div className="text-red-400 mb-2">⚠️ Error loading cost data</div>
        <div className="text-sm text-gray-500">{error}</div>
        <button
          onClick={fetchCostData}
          className="mt-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  const formatCost = (cost: number) => {
    if (cost < 0.01) return `$${(cost * 100).toFixed(2)}¢`;
    return `$${cost.toFixed(2)}`;
  };

  const formatPercentage = (value: number) => `${value.toFixed(1)}%`;

  return (
    <div className="p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Cost Dashboard</h2>
          <p className="text-sm text-gray-400">
            Last 24 hours • {summary.total_requests.toLocaleString()} requests
          </p>
        </div>
        <button
          onClick={fetchCostData}
          className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm"
        >
          Refresh
        </button>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Spent"
          value={formatCost(summary.total_cost)}
          icon="💰"
          trend={summary.total_cost > 0 ? "neutral" : "good"}
        />
        <StatCard
          label="Avg / Request"
          value={formatCost(summary.avg_cost_per_request)}
          icon="📊"
        />
        <StatCard
          label="Requests"
          value={summary.total_requests.toLocaleString()}
          icon="⚡"
        />
        <StatCard
          label="Saved by Routing"
          value={formatCost(summary.estimated_savings_from_routing)}
          icon="💚"
          highlight={summary.estimated_savings_from_routing > 0}
        />
      </div>

      {/* Budget Progress */}
      {budgetStatus && (budgetStatus.daily.budget || budgetStatus.monthly.budget) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {budgetStatus.daily.budget && (
            <BudgetCard
              title="Daily Budget"
              spent={budgetStatus.daily.spent}
              budget={budgetStatus.daily.budget}
              percentage={budgetStatus.daily.percentage}
            />
          )}
          {budgetStatus.monthly.budget && (
            <BudgetCard
              title="Monthly Budget"
              spent={budgetStatus.monthly.spent}
              budget={budgetStatus.monthly.budget}
              percentage={budgetStatus.monthly.percentage}
            />
          )}
        </div>
      )}

      {/* Model Cost Distribution */}
      <div className="bg-gray-800/50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-white mb-4">Cost by Model</h3>

        {Object.keys(summary.cost_by_model).length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No cost data available yet. Make some requests to see cost breakdown.
          </div>
        ) : (
          <div className="space-y-3">
            {Object.entries(summary.cost_by_model)
              .sort(([, a], [, b]) => b - a)
              .map(([model, cost]) => {
                const percentage = summary.total_cost > 0 ? (cost / summary.total_cost) * 100 : 0;
                const tokens = summary.tokens_by_model[model] || 0;

                return (
                  <div key={model} className="flex items-center gap-4">
                    <div className="w-24 text-sm text-gray-300 truncate">
                      {model}
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-400">
                          {formatCost(cost)} • {tokens.toLocaleString()} tokens
                        </span>
                        <span className="text-gray-500">
                          {formatPercentage(percentage)}
                        </span>
                      </div>
                      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            percentage > 50 ? 'bg-red-500' :
                            percentage > 25 ? 'bg-yellow-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>

      {/* Savings Highlight */}
      {summary.estimated_savings_from_routing > 0 && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="text-3xl">🎉</div>
            <div className="flex-1">
              <h3 className="text-green-400 font-semibold">
                Intelligent routing saved you {formatCost(summary.estimated_savings_from_routing)} today!
              </h3>
              <p className="text-sm text-green-500/70 mt-1">
                By automatically selecting the cheapest suitable model for each query type.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Cost Efficiency Tips */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <h3 className="text-blue-400 font-semibold mb-2">💡 Cost Optimization Tips</h3>
        <ul className="text-sm text-blue-300/80 space-y-1">
          <li>• Use "cost" priority for maximum savings on non-critical queries</li>
          <li>• Set daily/monthly budgets to prevent overspending</li>
          <li>• GPT-4o-mini handles 90%+ of queries at 97% cost savings</li>
          <li>• Routing decisions cost only $0.00005 each (negligible)</li>
        </ul>
      </div>
    </div>
  );
};

// Stat Card Component
const StatCard: React.FC<{
  label: string;
  value: string;
  icon: string;
  trend?: "good" | "bad" | "neutral";
  highlight?: boolean;
}> = ({ label, value, icon, trend, highlight }) => (
  <div
    className={`p-4 rounded-lg ${
      highlight
        ? 'bg-green-500/10 border border-green-500/30'
        : 'bg-gray-800/50'
    }`}
  >
    <div className="flex items-center gap-2 mb-2">
      <span className="text-lg">{icon}</span>
      <span className="text-xs text-gray-500">{label}</span>
    </div>
    <p className={`text-xl font-semibold ${
      highlight ? 'text-green-400' :
      trend === "good" ? 'text-green-400' :
      trend === "bad" ? 'text-red-400' : 'text-white'
    }`}>
      {value}
    </p>
  </div>
);

// Budget Card Component
const BudgetCard: React.FC<{
  title: string;
  spent: number;
  budget: number;
  percentage: number | null;
}> = ({ title, spent, budget, percentage }) => {
  const formatCost = (cost: number) => {
    if (cost < 0.01) return `$${(cost * 100).toFixed(2)}¢`;
    return `$${cost.toFixed(2)}`;
  };

  const getStatusColor = (pct: number | null) => {
    if (!pct) return "bg-gray-500";
    if (pct >= 90) return "bg-red-500";
    if (pct >= 70) return "bg-yellow-500";
    return "bg-green-500";
  };

  return (
    <div className="bg-gray-800/50 rounded-lg p-4">
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-sm font-medium text-gray-300">{title}</h4>
        <span className="text-xs text-gray-500">
          {formatCost(spent)} / {formatCost(budget)}
        </span>
      </div>
      <div className="h-3 bg-gray-700 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full transition-all ${getStatusColor(percentage)}`}
          style={{ width: `${Math.min(percentage || 0, 100)}%` }}
        />
      </div>
      {percentage !== null && (
        <div className="text-xs text-gray-400">
          {percentage.toFixed(1)}% used
          {percentage >= 90 && (
            <span className="text-red-400 ml-2">⚠️ Near limit</span>
          )}
        </div>
      )}
    </div>
  );
};

export default CostDashboard;
