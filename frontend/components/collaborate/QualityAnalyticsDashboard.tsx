"use client";

import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { TrendingUp, TrendingDown, AlertCircle, CheckCircle2 } from "lucide-react";

export interface QualityAnalyticsData {
  run_id: string;
  timestamp: string;
  query_complexity: number;
  overall_score: number;
  substance_score: number;
  completeness_score: number;
  depth_score: number;
  accuracy_score: number;
  quality_gate_passed: boolean;
}

interface QualityAnalyticsDashboardProps {
  data: QualityAnalyticsData[];
  title?: string;
  description?: string;
}

const COLORS = {
  passed: "#10b981", // green-500
  failed: "#f59e0b", // yellow-500
  level1: "#6b7280", // gray-500
  level2: "#3b82f6", // blue-500
  level3: "#8b5cf6", // purple-500
  level4: "#f59e0b", // yellow-500
  level5: "#ef4444", // red-500
};

const ComplexityDistributionChart: React.FC<{ data: QualityAnalyticsData[] }> = ({ data }) => {
  const distributionData = useMemo(() => {
    const counts = data.reduce((acc, item) => {
      const level = item.query_complexity;
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    }, {} as Record<number, number>);

    return Object.entries(counts).map(([level, count]) => ({
      name: `Level ${level}`,
      value: count,
      color: (COLORS as any)[`level${level}`] || COLORS.level3,
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={distributionData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {distributionData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
};

const QualityTrendChart: React.FC<{ data: QualityAnalyticsData[] }> = ({ data }) => {
  const chartData = useMemo(() => {
    return data.slice(-20).map((item, index) => ({
      index: index + 1,
      overall: item.overall_score,
      substance: item.substance_score,
      completeness: item.completeness_score,
      depth: item.depth_score,
      accuracy: item.accuracy_score,
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="index" label={{ value: "Run #", position: "insideBottom", offset: -5 }} />
        <YAxis domain={[0, 10]} label={{ value: "Score", angle: -90, position: "insideLeft" }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="overall" stroke="#8884d8" strokeWidth={2} name="Overall" />
        <Line type="monotone" dataKey="substance" stroke="#82ca9d" name="Substance" />
        <Line type="monotone" dataKey="completeness" stroke="#ffc658" name="Completeness" />
        <Line type="monotone" dataKey="depth" stroke="#ff7c7c" name="Depth" />
        <Line type="monotone" dataKey="accuracy" stroke="#a28fd0" name="Accuracy" />
      </LineChart>
    </ResponsiveContainer>
  );
};

const ScoresByComplexityChart: React.FC<{ data: QualityAnalyticsData[] }> = ({ data }) => {
  const chartData = useMemo(() => {
    // Group by complexity and calculate average scores
    const grouped = data.reduce((acc, item) => {
      const level = item.query_complexity;
      if (!acc[level]) {
        acc[level] = {
          count: 0,
          totalOverall: 0,
          totalSubstance: 0,
          totalCompleteness: 0,
          totalDepth: 0,
          totalAccuracy: 0,
        };
      }
      acc[level].count++;
      acc[level].totalOverall += item.overall_score;
      acc[level].totalSubstance += item.substance_score;
      acc[level].totalCompleteness += item.completeness_score;
      acc[level].totalDepth += item.depth_score;
      acc[level].totalAccuracy += item.accuracy_score;
      return acc;
    }, {} as Record<number, any>);

    return Object.entries(grouped).map(([level, stats]) => ({
      name: `Level ${level}`,
      overall: stats.totalOverall / stats.count,
      substance: stats.totalSubstance / stats.count,
      completeness: stats.totalCompleteness / stats.count,
      depth: stats.totalDepth / stats.count,
      accuracy: stats.totalAccuracy / stats.count,
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis domain={[0, 10]} />
        <Tooltip />
        <Legend />
        <Bar dataKey="overall" fill="#8884d8" name="Overall" />
        <Bar dataKey="substance" fill="#82ca9d" name="Substance" />
        <Bar dataKey="completeness" fill="#ffc658" name="Completeness" />
        <Bar dataKey="depth" fill="#ff7c7c" name="Depth" />
        <Bar dataKey="accuracy" fill="#a28fd0" name="Accuracy" />
      </BarChart>
    </ResponsiveContainer>
  );
};

const StatCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  icon?: React.ReactNode;
}> = ({ title, value, subtitle, trend, icon }) => {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
          </div>
          {icon && <div className="text-gray-400">{icon}</div>}
        </div>
        {trend && (
          <div className="mt-2 flex items-center gap-1">
            {trend === "up" && (
              <>
                <TrendingUp className="h-3 w-3 text-green-600" />
                <span className="text-xs text-green-600">Improving</span>
              </>
            )}
            {trend === "down" && (
              <>
                <TrendingDown className="h-3 w-3 text-red-600" />
                <span className="text-xs text-red-600">Declining</span>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export const QualityAnalyticsDashboard: React.FC<QualityAnalyticsDashboardProps> = ({
  data,
  title = "Quality Analytics Dashboard",
  description = "Track quality metrics across all collaboration runs",
}) => {
  const stats = useMemo(() => {
    if (data.length === 0) {
      return {
        avgOverall: 0,
        passRate: 0,
        totalRuns: 0,
        avgByComplexity: {},
        recentTrend: "neutral" as const,
      };
    }

    const totalRuns = data.length;
    const passed = data.filter((d) => d.quality_gate_passed).length;
    const avgOverall = data.reduce((sum, d) => sum + d.overall_score, 0) / totalRuns;

    // Calculate average by complexity
    const avgByComplexity = data.reduce((acc, item) => {
      const level = item.query_complexity;
      if (!acc[level]) {
        acc[level] = { sum: 0, count: 0 };
      }
      acc[level].sum += item.overall_score;
      acc[level].count++;
      return acc;
    }, {} as Record<number, { sum: number; count: number }>);

    // Calculate trend (compare last 5 vs previous 5)
    let recentTrend: "up" | "down" | "neutral" = "neutral";
    if (data.length >= 10) {
      const recent5 = data.slice(-5);
      const previous5 = data.slice(-10, -5);
      const recentAvg = recent5.reduce((sum, d) => sum + d.overall_score, 0) / 5;
      const previousAvg = previous5.reduce((sum, d) => sum + d.overall_score, 0) / 5;

      if (recentAvg > previousAvg + 0.5) recentTrend = "up";
      else if (recentAvg < previousAvg - 0.5) recentTrend = "down";
    }

    return {
      avgOverall,
      passRate: (passed / totalRuns) * 100,
      totalRuns,
      avgByComplexity,
      recentTrend,
    };
  }, [data]);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-center text-gray-500 py-8">
            No quality data available yet. Run some collaborations to see analytics.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Average Quality"
          value={stats.avgOverall.toFixed(1)}
          subtitle="Overall score across all runs"
          trend={stats.recentTrend}
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <StatCard
          title="Pass Rate"
          value={`${stats.passRate.toFixed(0)}%`}
          subtitle={`${data.filter((d) => d.quality_gate_passed).length} of ${stats.totalRuns} runs`}
          icon={stats.passRate >= 70 ? <CheckCircle2 className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
        />
        <StatCard
          title="Total Runs"
          value={stats.totalRuns}
          subtitle="Collaboration runs analyzed"
        />
        <StatCard
          title="Avg Complexity"
          value={`Level ${(data.reduce((sum, d) => sum + d.query_complexity, 0) / data.length).toFixed(1)}`}
          subtitle="Query complexity"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Quality Trend (Last 20 Runs)</CardTitle>
            <CardDescription>Track quality scores over time</CardDescription>
          </CardHeader>
          <CardContent>
            <QualityTrendChart data={data} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Query Complexity Distribution</CardTitle>
            <CardDescription>Breakdown of query complexity levels</CardDescription>
          </CardHeader>
          <CardContent>
            <ComplexityDistributionChart data={data} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Average Scores by Complexity Level</CardTitle>
          <CardDescription>Compare quality metrics across different complexity levels</CardDescription>
        </CardHeader>
        <CardContent>
          <ScoresByComplexityChart data={data} />
        </CardContent>
      </Card>
    </div>
  );
};

export default QualityAnalyticsDashboard;
