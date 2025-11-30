"use client";

import { usePathname } from "next/navigation";

interface ConditionalLayoutProps {
  children: React.ReactNode;
}

export function ConditionalLayout({ children }: ConditionalLayoutProps) {
  const pathname = usePathname();

  // Hide header and footer on conversation pages
  const isConversationPage = pathname.startsWith('/conversations');

  if (isConversationPage) {
    return <div className="h-screen w-full overflow-hidden">{children}</div>;
  }

  return (
    <>
      <main className="flex-1">{children}</main>
    </>
  );
}