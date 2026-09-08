import { AppHeader, RequireAuth } from "@/components/app-shell";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <RequireAuth>
      <div className="flex min-h-screen flex-col bg-zinc-50 dark:bg-zinc-950">
        <AppHeader />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
      </div>
    </RequireAuth>
  );
}
