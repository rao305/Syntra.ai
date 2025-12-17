import { cn } from '@/lib/utils';
import { Bot, User } from 'lucide-react';
import React from 'react';
import { EnhancedMessageContent } from './enhanced-message-content';

interface MessageProps {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: Date;
    model?: string;
    isCollaboration?: boolean;
}

export const EnhancedMessageBubble: React.FC<MessageProps> = ({
    role,
    content,
    timestamp,
    model,
    isCollaboration,
}) => {
    const isUser = role === 'user';

    return (
        <div
            className={cn(
                "message-container py-6 px-4 transition-colors duration-200",
                isUser ? "bg-transparent" : "bg-zinc-900/30 hover:bg-zinc-900/50"
            )}
        >
            <div className={cn("max-w-4xl mx-auto flex gap-4", isUser ? "justify-end" : "justify-start")}>
                {/* Assistant Avatar */}
                {!isUser && (
                    <div className="flex-shrink-0 mt-1">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                            <Bot className="w-4 h-4 text-white" />
                        </div>
                    </div>
                )}

                <div className={cn("flex flex-col max-w-[85%]", isUser ? "items-end" : "items-start")}>
                    {/* Header */}
                    <div className="flex items-center gap-2 mb-1.5 px-1">
                        <span className="text-sm font-medium text-zinc-300">
                            {isUser ? "You" : "Syntra"}
                        </span>

                        {!isUser && isCollaboration && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded-full font-medium tracking-wide">
                                COLLABORATED
                            </span>
                        )}

                        {!isUser && model && !isCollaboration && (
                            <span className="text-xs text-zinc-500 font-mono">
                                {model}
                            </span>
                        )}

                        {timestamp && (
                            <span className="text-xs text-zinc-600">
                                {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        )}
                    </div>

                    {/* Message Content */}
                    <div className={cn(
                        "rounded-2xl px-5 py-3.5",
                        isUser
                            ? "bg-zinc-800 text-zinc-100 border border-zinc-700/50 rounded-tr-sm"
                            : "bg-transparent p-0"
                    )}>
                        {isUser ? (
                            <div className="whitespace-pre-wrap leading-relaxed">{content}</div>
                        ) : (
                            <EnhancedMessageContent
                                content={content}
                                role="assistant"
                            />
                        )}
                    </div>
                </div>

                {/* User Avatar */}
                {isUser && (
                    <div className="flex-shrink-0 mt-1">
                        <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                            <User className="w-4 h-4 text-zinc-400" />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

