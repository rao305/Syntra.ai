import React from 'react';

interface WelcomeScreenProps {
  onSendMessage: (message: string) => void;
  onStartCollaboration?: (message: string, orgId: string) => void;
  orgId?: string;
}

const QUICK_ACTIONS = [
  { icon: '💡', label: 'Analyze', prompt: 'Help me analyze' },
  { icon: '💻', label: 'Code', prompt: 'Help me write code for' },
  { icon: '✨', label: 'Brainstorm', prompt: 'Help me brainstorm ideas for' },
  { icon: '📝', label: 'Write', prompt: 'Help me write' },
];

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onSendMessage }) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      {/* Minimal Logo */}
      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-white/10 flex items-center justify-center mb-6">
        <span className="text-2xl">🧠</span>
      </div>

      {/* Headline */}
      <h1 className="text-2xl font-medium text-white mb-2">
        What can I help you with?
      </h1>

      {/* Subtle subtitle with hover tooltip */}
      <div className="group relative mb-10">
        <p className="text-sm text-gray-500 cursor-default">
          Powered by multiple AI models working together
        </p>
        
        {/* Tooltip - only shows on hover */}
        <div className="
          absolute left-1/2 -translate-x-1/2 top-full mt-2
          opacity-0 group-hover:opacity-100
          transition-opacity duration-200
          flex gap-2 px-3 py-2 bg-gray-800 rounded-lg
          text-xs whitespace-nowrap border border-gray-700 pointer-events-none z-10
        ">
          <span className="flex items-center gap-1"><span className="text-[10px]">🟢</span> GPT-4o</span>
          <span className="flex items-center gap-1"><span className="text-[10px]">🔵</span> Gemini</span>
          <span className="flex items-center gap-1"><span className="text-[10px]">🟣</span> Claude</span>
          <span className="flex items-center gap-1"><span className="text-[10px]">🟠</span> Perplexity</span>
        </div>
      </div>

      {/* Quick Actions - Single Row */}
      <div className="flex flex-wrap justify-center gap-2">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.label}
            onClick={() => onSendMessage(action.prompt)}
            className="
              flex items-center gap-2 px-4 py-2
              text-sm text-gray-400
              bg-white/5 hover:bg-white/10
              border border-white/5 hover:border-white/10
              rounded-full transition-all duration-200
              hover:text-white
            "
          >
            <span>{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default WelcomeScreen;
