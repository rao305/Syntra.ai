import { useEffect } from 'react';

interface Shortcuts {
  onNewChat?: () => void;
  onFocusInput?: () => void;
  onToggleSidebar?: () => void;
}

export const useKeyboardShortcuts = ({ onNewChat, onFocusInput, onToggleSidebar }: Shortcuts) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const modifier = isMac ? e.metaKey : e.ctrlKey;

      // Cmd/Ctrl + K: New Chat
      if (modifier && e.key === 'k') {
        e.preventDefault();
        onNewChat?.();
      }

      // Cmd/Ctrl + /: Focus Input
      if (modifier && e.key === '/') {
        e.preventDefault();
        onFocusInput?.();
      }

      // Cmd/Ctrl + B: Toggle Sidebar
      if (modifier && e.key === 'b') {
        e.preventDefault();
        onToggleSidebar?.();
      }

      // Escape: Blur input / Close modals
      if (e.key === 'Escape') {
        (document.activeElement as HTMLElement)?.blur();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onNewChat, onFocusInput, onToggleSidebar]);
};
