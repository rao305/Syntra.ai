"use client";

import React, { useState, useEffect } from 'react';

interface SimpleLoadingStateProps {
  model?: string;
  isCollaboration?: boolean;
}

export const SimpleLoadingState: React.FC<SimpleLoadingStateProps> = ({
  model,
  isCollaboration = false,
}) => {
  const [messageIndex, setMessageIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  const messages = isCollaboration
    ? [
        "Assembling AI council...",
        "Models are deliberating...",
        "Synthesizing perspectives...",
        "Crafting unified response...",
      ]
    : [
        "Thinking...",
        "Processing your request...",
        "Analyzing context...",
        "Generating response...",
      ];

  useEffect(() => {
    const messageInterval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % messages.length);
    }, 2000);

    const timeInterval = setInterval(() => {
      setElapsed((prev) => prev + 100);
    }, 100);

    return () => {
      clearInterval(messageInterval);
      clearInterval(timeInterval);
    };
  }, [messages.length]);

  const getModelEmoji = (m: string) => {
    if (m?.toLowerCase().includes('gpt')) return '🟢';
    if (m?.toLowerCase().includes('gemini')) return '🔵';
    if (m?.toLowerCase().includes('claude')) return '🟣';
    if (m?.toLowerCase().includes('perplexity')) return '🟠';
    return '🤖';
  };

  return (
    <div className="flex items-start gap-3 py-4 px-2">
      {/* Animated Avatar */}
      <div className="relative flex-shrink-0">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-[2px]">
          <div className="w-full h-full rounded-full bg-gray-900 flex items-center justify-center">
            <svg
              className="w-5 h-5 text-purple-400 animate-pulse"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
            </svg>
          </div>
        </div>
        {/* Spinning ring */}
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-purple-500 animate-spin" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Status */}
        <div className="flex items-center gap-2 flex-wrap">
          {isCollaboration && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-500/20 text-purple-300 text-xs rounded-full">
              <span>✨</span>
              <span>Collaborating</span>
            </span>
          )}
          {model && (
            <span className="inline-flex items-center gap-1 text-xs text-gray-500">
              {getModelEmoji(model)} {model}
            </span>
          )}
        </div>

        {/* Message */}
        <p className="text-sm text-gray-400 mt-1 transition-opacity duration-300">
          {messages[messageIndex]}
        </p>

        {/* Typing Indicator with Timer */}
        <div className="flex items-center gap-3 mt-2">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 bg-purple-500/70 rounded-full animate-bounce"
                style={{
                  animationDelay: `${i * 0.15}s`,
                }}
              />
            ))}
          </div>
          <span className="text-xs text-gray-600">
            {(elapsed / 1000).toFixed(1)}s
          </span>
        </div>
      </div>
    </div>
  );
};

export default SimpleLoadingState;
