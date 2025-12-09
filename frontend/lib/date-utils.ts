/**
 * Date formatting utilities for thread display
 */

export function formatThreadDate(date: Date | string): string {
    const dateObj = typeof date === "string" ? new Date(date) : date;
    const now = new Date();
    const diffMs = now.getTime() - dateObj.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    // Less than a minute ago
    if (diffMinutes < 1) {
        return "Just now";
    }

    // Less than an hour ago
    if (diffMinutes < 60) {
        return `${diffMinutes}m ago`;
    }

    // Less than a day ago
    if (diffHours < 24) {
        return `${diffHours}h ago`;
    }

    // Today
    if (diffDays === 0) {
        return "Today";
    }

    // Yesterday
    if (diffDays === 1) {
        return "Yesterday";
    }

    // Within last week
    if (diffDays < 7) {
        return `${diffDays} days ago`;
    }

    // Within last month
    if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        return `${weeks} ${weeks === 1 ? "week" : "weeks"} ago`;
    }

    // Older than a month - show date
    return dateObj.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: dateObj.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
    });
}

export function groupThreadsByDate(threads: Array<{ updated_at: string | null; created_at: string }>): {
    today: typeof threads;
    yesterday: typeof threads;
    thisWeek: typeof threads;
    thisMonth: typeof threads;
    older: typeof threads;
} {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);
    const monthAgo = new Date(today);
    monthAgo.setMonth(monthAgo.getMonth() - 1);

    const groups = {
        today: [] as typeof threads,
        yesterday: [] as typeof threads,
        thisWeek: [] as typeof threads,
        thisMonth: [] as typeof threads,
        older: [] as typeof threads,
    };

    threads.forEach((thread) => {
        const threadDate = thread.updated_at
            ? new Date(thread.updated_at)
            : new Date(thread.created_at);

        if (threadDate >= today) {
            groups.today.push(thread);
        } else if (threadDate >= yesterday) {
            groups.yesterday.push(thread);
        } else if (threadDate >= weekAgo) {
            groups.thisWeek.push(thread);
        } else if (threadDate >= monthAgo) {
            groups.thisMonth.push(thread);
        } else {
            groups.older.push(thread);
        }
    });

    return groups;
}

export function getDateGroupLabel(group: "today" | "yesterday" | "thisWeek" | "thisMonth" | "older"): string {
    switch (group) {
        case "today":
            return "Today";
        case "yesterday":
            return "Yesterday";
        case "thisWeek":
            return "Previous 7 days";
        case "thisMonth":
            return "Previous 30 days";
        case "older":
            return "Older";
        default:
            return "";
    }
}

