"use client";

import React from 'react';

export const SkeletonResponse: React.FC = () => {
  return (
    <div className="space-y-3 py-4 animate-pulse">
      {/* Simulated text lines */}
      <div className="h-4 bg-gray-700/50 rounded w-3/4 animate-shimmer" />
      <div className="h-4 bg-gray-700/50 rounded w-full animate-shimmer" />
      <div className="h-4 bg-gray-700/50 rounded w-5/6 animate-shimmer" />
      <div className="h-4 bg-gray-700/50 rounded w-2/3 animate-shimmer" />

      {/* Simulated code block */}
      <div className="mt-4 rounded-lg border border-gray-700/50 overflow-hidden">
        <div className="h-8 bg-gray-800/50 animate-shimmer" />
        <div className="p-4 space-y-2">
          <div className="h-3 bg-gray-700/30 rounded w-1/2 animate-shimmer" />
          <div className="h-3 bg-gray-700/30 rounded w-3/4 animate-shimmer" />
          <div className="h-3 bg-gray-700/30 rounded w-2/3 animate-shimmer" />
        </div>
      </div>
    </div>
  );
};

export default SkeletonResponse;
