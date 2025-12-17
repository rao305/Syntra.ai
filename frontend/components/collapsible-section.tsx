import { ChevronDown, ChevronRight } from 'lucide-react';
import React, { useState } from 'react';

interface CollapsibleSectionProps {
    title: React.ReactNode;
    children: React.ReactNode;
    defaultOpen?: boolean;
    level?: 1 | 2 | 3;
    className?: string;
}

export const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
    title,
    children,
    defaultOpen = true,
    level = 2,
    className = '',
}) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    const headingStyles = {
        1: 'text-xl font-bold',
        2: 'text-lg font-semibold',
        3: 'text-base font-medium',
    };

    return (
        <div className={`collapsible-section mb-4 ${className}`}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 w-full text-left group hover:bg-white/5 p-1 rounded-md -ml-1 transition-colors"
            >
                {isOpen ? (
                    <ChevronDown className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 transition-colors flex-shrink-0" />
                ) : (
                    <ChevronRight className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 transition-colors flex-shrink-0" />
                )}
                <div className={`${headingStyles[level]} text-zinc-200 group-hover:text-white transition-colors flex-1`}>
                    {title}
                </div>
            </button>
            {isOpen && (
                <div className="mt-2 pl-2 border-l-2 border-zinc-800 ml-2 animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="pl-4">
                        {children}
                    </div>
                </div>
            )}
        </div>
    );
};

